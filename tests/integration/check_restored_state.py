"""Relire l'état métier réel après redémarrage ; aucun objet de test créé."""

import argparse
import json
import os
from pathlib import Path
import urllib.request

import psycopg
from pymongo import MongoClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--expected-scores", type=int, required=True)
    parser.add_argument("--expected-alerts", type=int, required=True)
    parser.add_argument("--minimum-decisions", type=int, required=True)
    parser.add_argument("--check-llm", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.expected_alerts <= args.expected_scores or args.minimum_decisions < 0:
        parser.error("Comptages attendus invalides")
    with psycopg.connect(host="postgres", dbname="bc1", user="bc1app",
                        password=os.environ["POSTGRES_APP_PASSWORD"], connect_timeout=5) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM analyst_decision")
            decisions = cursor.fetchone()[0]
    if decisions < args.minimum_decisions:
        raise AssertionError("Décisions SQL attendues absentes après redémarrage")
    with MongoClient("mongodb://mongo:27017", username="bc1app",
                     password=os.environ["MONGO_APP_PASSWORD"], authSource="fraud",
                     serverSelectionTimeoutMS=5000, socketTimeoutMS=5000) as client:
        query = {"model_version": args.model_version}
        scores = client.fraud.fraud_scores.count_documents(query, maxTimeMS=5000)
        alerts = client.fraud.fraud_scores.count_documents({**query, "is_alert": True}, maxTimeMS=5000)
    if (scores, alerts) != (args.expected_scores, args.expected_alerts):
        raise AssertionError(f"Comptages Mongo différents de la référence : {scores} scores, {alerts} alertes")
    with urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=10) as response:
        if response.status != 200:
            raise AssertionError("API indisponible après redémarrage")
    if args.check_llm:
        lock = json.loads(Path("infra/llm.lock.json").read_text())
        with urllib.request.urlopen("http://ollama:11434/api/tags", timeout=15) as response:
            models = json.load(response)["models"]
        if not any(model["name"] == lock["model"] and model["digest"] == lock["digest"] for model in models):
            raise AssertionError("Modèle LLM verrouillé absent")
    print(json.dumps({"event": "retained_state_verified", "model_version": args.model_version,
                      "api_ready": 200, "scores": scores, "alerts": alerts,
                      "sql_decisions": decisions, "llm_digest_checked": args.check_llm,
                      "scope": "counts and readiness; HDFS verification runs separately"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
