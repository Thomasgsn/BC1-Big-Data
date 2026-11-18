"""Préparer et profiler PaySim sans charger le CSV en mémoire."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any
import zipfile


HEADERS = (
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
)
TYPES = frozenset({"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"})
DECIMAL_FIELDS = ("amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest")
EXCLUDED_FEATURES = (*DECIMAL_FIELDS[1:], "isFraud", "isFlaggedFraud")
SOURCE_URL = "https://www.kaggle.com/datasets/ealaxi/paysim1"
CSV_NAME = "PS_20174392719_1491204439457_log.csv"
MAX_UNCOMPRESSED_BYTES = 2_000_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, document: dict[str, Any]) -> None:
    """Publier un rapport complet ou conserver intact le rapport précédent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
        temporary = Path(out.name)
        try:
            json.dump(document, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write("\n")
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_archive(archive: Path, destination: Path) -> Path:
    """Extraire uniquement le CSV attendu, sans écraser un fichier existant."""
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / CSV_NAME
    if target.exists():
        raise FileExistsError(f"Le CSV existe déjà : {target}. Vérifier son empreinte avant réutilisation.")
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        if len(members) != 1 or members[0].filename != CSV_NAME:
            raise ValueError("L'archive doit contenir uniquement le CSV PaySim attendu, sans sous-dossier.")
        info = members[0]
        if info.is_dir() or info.file_size > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Taille ou type du contenu de l'archive refusé.")
        with tempfile.NamedTemporaryFile(dir=destination, delete=False) as output:
            temporary = Path(output.name)
            try:
                with zipped.open(info) as stream:
                    # ZipFile vérifie également le CRC à la fin de cette lecture complète.
                    shutil.copyfileobj(stream, output, length=1024 * 1024)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            if temporary.stat().st_size != info.file_size:
                raise ValueError("Taille extraite différente de la taille annoncée.")
            # Création exclusive pour éviter tout écrasement même en cas de concurrence.
            with target.open("xb") as output, temporary.open("rb") as stream:
                try:
                    shutil.copyfileobj(stream, output, length=1024 * 1024)
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
        finally:
            temporary.unlink(missing_ok=True)
    return target


def profile_csv(path: Path) -> dict[str, Any]:
    """Compter toutes les lignes et signaler les anomalies sans les corriger."""
    rows = 0
    invalid_rows = 0
    missing: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    fraud_by_type: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    flagged_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    ranges: dict[str, dict[str, Decimal]] = {}
    steps: Counter[int] = Counter()
    fraud_steps: Counter[int] = Counter()
    previous_step: int | None = None
    step_regressions = 0
    zero_amounts = 0
    max_decimal_places = 0

    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError(f"En-tête PaySim inattendu : {reader.fieldnames!r}")
        for rows, row in enumerate(reader, start=1):
            errors: list[str] = []
            if None in row:
                errors.append("extra_columns")
            for key in HEADERS:
                if row.get(key) is None or not str(row[key]).strip():
                    missing[key] += 1
                    errors.append(f"missing:{key}")
            transaction_type = row.get("type", "")
            type_counts[transaction_type or "<missing>"] += 1
            if transaction_type not in TYPES:
                errors.append("invalid:type")
            label = row.get("isFraud", "")
            label_counts[label or "<missing>"] += 1
            flagged = row.get("isFlaggedFraud", "")
            flagged_counts[flagged or "<missing>"] += 1
            for key, value in (("isFraud", label), ("isFlaggedFraud", flagged)):
                if value not in {"0", "1"}:
                    errors.append(f"invalid:{key}")
            if label == "1":
                fraud_by_type[transaction_type or "<missing>"] += 1
            try:
                raw_step = row.get("step") or ""
                if not raw_step.isascii() or not raw_step.isdigit():
                    raise ValueError
                step = int(raw_step)
                if step < 1:
                    raise ValueError
                if previous_step is not None and step < previous_step:
                    step_regressions += 1
                previous_step = step
                steps[step] += 1
                if label == "1":
                    fraud_steps[step] += 1
            except ValueError:
                errors.append("invalid:step")
            for key in DECIMAL_FIELDS:
                try:
                    value = Decimal(row.get(key) or "")
                    if not value.is_finite():
                        raise ValueError
                    bounds = ranges.setdefault(key, {"min": value, "max": value})
                    bounds["min"] = min(bounds["min"], value)
                    bounds["max"] = max(bounds["max"], value)
                    if value < 0:
                        errors.append(f"negative:{key}")
                    if key == "amount":
                        zero_amounts += value == 0
                        max_decimal_places = max(max_decimal_places, max(0, -int(value.as_tuple().exponent)))
                except (InvalidOperation, ValueError):
                    errors.append(f"invalid:{key}")
            if errors:
                invalid_rows += 1
                error_counts.update(errors)
                if len(examples) < 10:
                    examples.append({"source_row": rows, "errors": errors})

    if not rows:
        raise ValueError("Le CSV ne contient aucune transaction.")
    fraud_count = label_counts["1"]
    return {
        "profile_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {"source": SOURCE_URL, "version": 2, "file_name": path.name,
                    "bytes": path.stat().st_size, "sha256": sha256_file(path), "synthetic": True},
        "headers": list(HEADERS), "rows": rows, "invalid_rows": invalid_rows,
        "valid_rows": rows - invalid_rows, "missing_by_column": {k: missing[k] for k in HEADERS},
        "types": dict(sorted(type_counts.items())), "labels": dict(sorted(label_counts.items())),
        "fraud_rows": fraud_count, "fraud_rate": str(Decimal(fraud_count) / Decimal(rows)),
        "fraud_by_type": dict(sorted(fraud_by_type.items())),
        "flagged_labels": dict(sorted(flagged_counts.items())),
        "numeric_ranges": {k: {b: str(v) for b, v in bounds.items()} for k, bounds in ranges.items()},
        "amount_zero_rows": zero_amounts, "amount_max_decimal_places": max_decimal_places,
        "step": {"min": min(steps) if steps else None, "max": max(steps) if steps else None,
                 "distinct": len(steps), "regressions": step_regressions,
                 "rows_by_step": dict(sorted(steps.items())), "fraud_by_step": dict(sorted(fraud_steps.items()))},
        "errors": dict(sorted(error_counts.items())), "error_examples": examples,
        "excluded_predictive_features": list(EXCLUDED_FEATURES),
        "limitations": ["Aucun contrôle d'unicité des comptes ou des transactions par contenu.",
                        "Les valeurs nulles métier de solde ne sont pas assimilées à des champs vides.",
                        "Les horodatages intrahoraires ne sont pas disponibles dans le CSV.",
                        "Les bornes et labels sont descriptifs, pas des performances de modèle."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="Extraire le CSV depuis l'archive locale")
    extract.add_argument("--archive", type=Path, required=True)
    extract.add_argument("--destination", type=Path, default=Path("data/raw"))
    profile = sub.add_parser("profile", help="Profiler intégralement le CSV local")
    profile.add_argument("--csv", type=Path, required=True)
    profile.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "extract":
            result = prepare_archive(args.archive, args.destination)
            print(json.dumps({"event": "dataset_extracted", "file": str(result),
                              "archive_sha256": sha256_file(args.archive)}, ensure_ascii=False))
            return 0
        report = profile_csv(args.csv)
        write_json(args.output, report)
        print(json.dumps({"event": "dataset_profiled", "rows": report["rows"],
                          "invalid_rows": report["invalid_rows"], "report": str(args.output)}, ensure_ascii=False))
        return 1 if report["invalid_rows"] else 0
    except (OSError, ValueError, zipfile.BadZipFile, csv.Error) as error:
        print(json.dumps({"event": "dataset_error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
