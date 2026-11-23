"""Rejeu PaySim JSONL ou Kafka ; le mode JSONL ne prouve pas l'ingestion Kafka."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import tempfile

from rncp_bc1.dataset import HEADERS, sha256_file
from rncp_bc1.transactions import ReplayContext, envelope


def selected_source_row(dataset_sha256: str, source_row: int, modulus: int = 1, seed: int = 42) -> bool:
    """Sélection déterministe indépendante des labels et valeurs de la transaction."""
    if modulus < 1:
        raise ValueError("Le module d'échantillonnage doit être positif.")
    if modulus == 1:
        return True
    digest = hashlib.sha256(f"{dataset_sha256}:{source_row}:sample:{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % modulus == 0


def selected_destination(dataset_sha256: str, destination: str, modulus: int = 1, seed: int = 42) -> bool:
    """Sélection par compte destinataire : garde tout l'historique des comptes retenus, sans lire les labels."""
    if modulus < 1:
        raise ValueError("Le module d'échantillonnage doit être positif.")
    if modulus == 1:
        return True
    digest = hashlib.sha256(f"{dataset_sha256}:{destination}:destination-sample:{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % modulus == 0


SAMPLE_KEYS = ("row", "destination")


def events(csv_path: Path, context: ReplayContext, start_row: int = 1, limit: int | None = None,
           sample_modulus: int = 1, sample_seed: int = 42, sample_key: str = "row"):
    if start_row < 1 or (limit is not None and limit < 1):
        raise ValueError("start_row et limit doivent être positifs.")
    if sample_key not in SAMPLE_KEYS:
        raise ValueError("Clé d'échantillonnage inconnue : row ou destination.")
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError("En-tête CSV PaySim inattendu.")
        sent = 0
        for position, row in enumerate(reader, 1):
            if position < start_row:
                continue
            if sample_key == "row":
                keep = selected_source_row(context.dataset_sha256, position, sample_modulus, sample_seed)
            else:
                keep = selected_destination(context.dataset_sha256, row.get("nameDest") or "", sample_modulus, sample_seed)
            if not keep:
                continue
            if None in row:
                raise ValueError(f"Colonnes supplémentaires à la ligne source {position}.")
            try:
                yield envelope(row, position, context)
            except ValueError as error:
                raise ValueError(f"Ligne source {position} : {error}") from error
            sent += 1
            if limit is not None and sent >= limit:
                break
        if not sent:
            raise ValueError("Aucune ligne sélectionnée pour le rejeu.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--epoch-utc", default="2000-01-01T00:00:00+00:00")
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sample-modulus", type=int, default=1, help="1 : tout ; 64 : environ 1/64 des positions, sans utiliser les labels")
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--sample-key", choices=SAMPLE_KEYS, default="row",
                        help="row : positions ; destination : comptes destinataires entiers (historique conservé)")
    parser.add_argument("--rate", type=float, default=100)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--jsonl", type=Path, help="Contrôle hors ligne, fichier créé exclusivement")
    destination.add_argument("--bootstrap-servers", help="Exemple interne : kafka:9092")
    parser.add_argument("--topic", default="transactions.v1")
    args = parser.parse_args()
    producer = None
    output = None
    temporary = None
    count = 0
    positives = 0
    last_source_row = args.start_row - 1
    started = time.monotonic()
    try:
        if args.rate <= 0 or not float("inf") > args.rate:
            raise ValueError("Le débit doit être positif et fini.")
        context = ReplayContext(args.sha256, args.run_id, args.epoch_utc)
        if args.sample_modulus < 1:
            raise ValueError("Le module d'échantillonnage doit être positif.")
        if sha256_file(args.csv) != args.sha256:
            raise ValueError("Empreinte dataset différente de celle attendue ; rejeu annulé.")
        if args.jsonl:
            args.jsonl.parent.mkdir(parents=True, exist_ok=True)
            if args.jsonl.exists():
                raise FileExistsError("Le fichier JSONL existe déjà ; aucun écrasement autorisé.")
            output = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.jsonl.parent, delete=False)
            temporary = Path(output.name)
        else:
            from kafka import KafkaProducer
            from rncp_bc1.security import producer_tls_options
            producer = KafkaProducer(bootstrap_servers=args.bootstrap_servers.split(","),
                                     **producer_tls_options(),
                                     acks="all", enable_idempotence=True,
                                     max_block_ms=30000, request_timeout_ms=30000,
                                     key_serializer=lambda key: key.encode("utf-8"),
                                     value_serializer=lambda value: json.dumps(value, allow_nan=False).encode("utf-8"))
        # Durée de rejeu séparée du coût du checksum et de la connexion.
        started = time.monotonic()
        for event in events(args.csv, context, args.start_row, args.limit, args.sample_modulus, args.sample_seed, args.sample_key):
            if output is not None:
                output.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
            else:
                # Attendre l'acquittement évite les erreurs cachées à la fermeture.
                producer.send(args.topic, key=event["payload"]["nameOrig"], value=event).get(timeout=35)
            count += 1
            positives += event["payload"]["isFraud"]
            last_source_row = event["source_row"]
            if count % 1000 == 0:
                print(json.dumps({"event": "replay_progress", "acknowledged_rows": count,
                                  "next_source_row": last_source_row+1}), file=sys.stderr)
            delay = count / args.rate - (time.monotonic() - started)
            if delay > 0:
                time.sleep(delay)
        if output:
            output.flush()
            os.fsync(output.fileno())
            output.close()
            output = None
            # Le lien publie le fichier complet sans remplacer une destination créée entre-temps.
            os.link(temporary, args.jsonl)
            temporary.unlink()
            temporary = None
        if producer:
            producer.flush(timeout=35)
            producer.close(timeout=5)
            producer = None
        elapsed = time.monotonic() - started
        print(json.dumps({"event": "replay_completed", "mode": "jsonl_control" if args.jsonl else "kafka",
                          "run_id": args.run_id, "acknowledged_rows": count,
                          "last_source_row": last_source_row, "positive_labels": positives,
                          "selection": {"sample_modulus": args.sample_modulus, "sample_seed": args.sample_seed, "sample_key": args.sample_key,
                                        "start_row": args.start_row, "maximum_events": args.limit},
                          "elapsed_seconds": elapsed, "observed_rows_per_second": count / elapsed}), file=sys.stderr)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(json.dumps({"event": "replay_failed", "acknowledged_rows": count,
                          "next_source_row": last_source_row+1,
                          "error_type": type(error).__name__, "message": str(error)}), file=sys.stderr)
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    finally:
        if output:
            output.close()
        if temporary:
            temporary.unlink(missing_ok=True)
        if producer:
            try:
                producer.close(timeout=5)
            except Exception as error:
                print(json.dumps({"event": "producer_close_failed", "error_type": type(error).__name__}), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
