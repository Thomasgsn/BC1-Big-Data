"""Appliquer un index de consultation de manière idempotente et vérifier son plan."""

import json
import os
from pymongo import MongoClient
from rncp_bc1.security import mongo_tls_options


def main():
    with MongoClient(host="mongo", username="bc1app", password=os.environ["MONGO_APP_PASSWORD"],
                     authSource="fraud", serverSelectionTimeoutMS=5000, **mongo_tls_options()) as client:
        database = client["fraud"]
        name = database.fraud_scores.create_index([("is_alert", 1), ("scored_at", -1), ("_id", 1)], name="alert_order")
        plan = database.command("explain", {"find": "fraud_scores", "filter": {"is_alert": True},
                                           "sort": {"scored_at": -1, "_id": 1}, "limit": 20})
        def indexes(value):
            if isinstance(value, dict):
                return ([value["indexName"]] if "indexName" in value else []) + [item for v in value.values() for item in indexes(v)]
            if isinstance(value, list):
                return [item for v in value for item in indexes(v)]
            return []
        used = indexes(plan["queryPlanner"]["winningPlan"])
        if name not in used:
            raise AssertionError("L'index de consultation attendu n'est pas sélectionné")
        print(json.dumps({"event": "data_lab_index_verified", "index": name, "winning_plan_indexes": used,
                          "scope": "Current alert filter/sort/limit, no general performance claim"}))


if __name__ == "__main__":
    main()
