"""Conversion d'un export MongoDB en CSV Gephi, avec intégrité des extrémités."""

import argparse
import csv
import hashlib
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import tempfile


def export_graph(document: dict, destination: Path) -> dict:
    nodes = document["nodes"]
    edges = document["edges"]
    if not nodes or not edges:
        raise ValueError("Le graphe à exporter doit comporter des nœuds et des arêtes.")
    if len(nodes) > 100000 or len(edges) > 50000:
        raise ValueError("Graphe trop grand pour ce profil Gephi ; sélectionner une fenêtre plus petite.")
    node_ids = [row["node_id"] for row in nodes]
    if len(set(node_ids)) != len(node_ids) or any(not re.fullmatch(r"[a-zA-Z0-9]{1,128}", x) for x in node_ids):
        raise ValueError("Identifiants de nœuds invalides ou dupliqués.")
    known = set(node_ids)
    edge_ids = set()
    for edge in edges:
        if edge["source"] not in known or edge["target"] not in known:
            raise ValueError("Arête référençant un nœud absent.")
        if edge["edge_id"] in edge_ids or not re.fullmatch(r"[0-9a-f]{64}", edge["edge_id"]):
            raise ValueError("Identifiant d'arête invalide ou dupliqué.")
        edge_ids.add(edge["edge_id"])
        if not isinstance(edge["transaction_count"], int) or isinstance(edge["transaction_count"], bool) or edge["transaction_count"] < 1:
            raise ValueError("Le nombre de transactions doit être un entier positif.")
        try:
            value = Decimal(str(edge["total_amount"]))
            if not value.is_finite() or value < 0:
                raise ValueError("Montant d'arête invalide.")
        except InvalidOperation as error:
            raise ValueError("Montant d'arête non décimal.") from error
    if destination.exists():
        raise FileExistsError("Destination existante ; choisir une nouvelle version d'export.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"snapshot_id": document["snapshot_id"], "nodes": len(nodes), "edges": len(edges),
                "origin": document.get("origin", "JSON input; origin not verified"), "directed": True, "weight": "transaction_count",
                "limitations": "Fenêtre filtrée ; hubs et communautés ne prouvent pas une fraude ou un blanchiment."}
    # Répertoire temporaire : un export invalide ne laisse pas de fichiers partiels publiés.
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        root = Path(temporary)/"export"
        root.mkdir()
        with (root/"nodes.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Id", "Label"])
            writer.writerows((x["node_id"], x["node_id"]) for x in sorted(nodes, key=lambda n: n["node_id"]))
        with (root/"edges.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Id", "Source", "Target", "Type", "Weight", "TotalAmount"])
            writer.writerows((x["edge_id"], x["source"], x["target"], "Directed", x["transaction_count"], str(x["total_amount"]))
                             for x in sorted(edges, key=lambda e: e["edge_id"]))
        metadata["files"] = {name: {"sha256": hashlib.sha256((root/name).read_bytes()).hexdigest()}
                             for name in ["nodes.csv", "edges.csv"]}
        (root/"manifest.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False)+"\n")
        root.rename(destination)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 100_000_000:
            raise ValueError("Export JSON trop volumineux.")
        report = export_graph(json.loads(args.input.read_text()), args.destination)
        print(json.dumps({"event": "gephi_exported", **report}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"event": "gephi_export_failed", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
