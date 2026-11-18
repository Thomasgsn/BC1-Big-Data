"""Injection volontaire de TROIS événements de test invalides, jamais des données métier."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from kafka import KafkaProducer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    with Path("/project/data/control/replay-10000.jsonl").open() as stream:
        base = json.loads(next(stream))
    base["replay_run_id"] = args.run_id
    base["emitted_at"] = datetime.now(timezone.utc).isoformat()
    base["fixture_origin"] = "AUTOMATED_INVALID_EVENT_TEST"
    cases = []
    for field, value in [("type", "INVALID_TEST_TYPE"), ("amount", "-1.00"), ("nameDest", "")]:
        event = deepcopy(base)
        event["payload"][field] = value
        cases.append(event)
    producer = KafkaProducer(bootstrap_servers="kafka:9092", acks="all", enable_idempotence=True)
    try:
        for event in cases:
            producer.send("transactions.v1", key=b"INVALID_TEST_FIXTURE", value=json.dumps(event).encode()).get(timeout=20)
    finally:
        producer.close(timeout=10)
    print(json.dumps({"event": "invalid_test_fixtures_acknowledged", "rows": 3, "run_id": args.run_id}))


if __name__ == "__main__":
    main()
