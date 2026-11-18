"""Sélection rétrospective sur labels PaySim pour évaluer le texte, jamais entrée du LLM."""

from datetime import datetime, timezone
import csv
import hashlib
import itertools
import json
from pathlib import Path

from rncp_bc1.api import mongo, serializable

digest = "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"
with Path("data/raw/PS_20174392719_1491204439457_log.csv").open() as stream:
    truth = {hashlib.sha256(f"{digest}:{index}".encode()).hexdigest(): int(row["isFraud"])
             for index, row in enumerate(itertools.islice(csv.DictReader(stream), 1000), 1)}
cases = {}
for score in mongo().fraud_scores.find({"run_id": "runtime-v1", "is_alert": True}).sort("transaction_id", 1):
    identifier = score["transaction_id"]
    label = truth[identifier]
    name = "true_positive" if label else "false_positive"
    if name not in cases:
        cases[name] = {"transaction_id": identifier, "score": score["score"], "threshold": score["threshold"],
                       "ground_truth_for_evaluation_only": label, "source_row": score["source_row"]}
if set(cases) != {"true_positive", "false_positive"}:
    raise AssertionError("Les deux cas d'évaluation ne sont pas disponibles ; aucun cas inventé")
print(json.dumps({"date": datetime.now(timezone.utc).isoformat(), "cases": cases,
                  "scope": "runtime demonstration prefix, not reserved ML test; labels never passed to the LLM"}))
