"""Événements SYNTHÉTIQUES de résilience, topic isolé RF3/ISR2 ; aucun dataset métier modifié."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer, TopicPartition


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()
    brokers = ["kafka:9092", "kafka-ha-101:9092", "kafka-ha-102:9092"]
    admin = KafkaAdminClient(bootstrap_servers=brokers, request_timeout_ms=10000)
    initial = admin.describe_topics([args.topic])[0]
    if initial["partitions"][0]["leader"] != 1 or set(initial["partitions"][0]["isr"]) != {1, 101, 102}:
        raise AssertionError("Leader initial ou ISR différents du protocole prévu")
    admin.close()
    producer = KafkaProducer(bootstrap_servers=brokers, acks="all", enable_idempotence=True,
                             retries=100, request_timeout_ms=10000, delivery_timeout_ms=60000)
    started, latencies, acknowledgements = time.monotonic(), [], []
    control = Path("/control")
    try:
        for index in range(220):
            if index == 20:
                ready = {"event": "ready_for_leader_stop", "topic": args.topic, "acknowledged_rows": index,
                         "time": now(), "initial_metadata": initial}
                (control/"ready.json").write_text(json.dumps(ready))
                print(json.dumps(ready), flush=True)
                deadline = time.monotonic()+120
                while not (control/"inject-now.json").exists():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Injection de panne non déclenchée ; aucun résultat de bascule revendiqué")
                    time.sleep(.1)
            begin = time.monotonic()
            event = {"fixture": "SYNTHETIC_KAFKA_RESILIENCE_TEST", "sequence": index}
            metadata = producer.send(args.topic, partition=0, key=str(index).encode(),
                                     value=json.dumps(event).encode()).get(timeout=65)
            latencies.append(time.monotonic()-begin)
            acknowledgements.append({"sequence": index, "offset": metadata.offset, "time": now()})
            time.sleep(max(0, .1-(time.monotonic()-begin)))
    finally:
        producer.close(timeout=10)
    consumer = KafkaConsumer(bootstrap_servers=brokers, group_id=None, enable_auto_commit=False,
                             request_timeout_ms=10000, session_timeout_ms=6000, heartbeat_interval_ms=2000)
    received = []
    try:
        consumer.assign([TopicPartition(args.topic, 0)])
        consumer.seek_to_beginning()
        deadline = time.monotonic()+30
        while len(received) < 220 and time.monotonic() < deadline:
            for batch in consumer.poll(timeout_ms=1000).values():
                received.extend(json.loads(message.value) for message in batch)
    finally:
        consumer.close()
    sequences = [x["sequence"] for x in received]
    if len(sequences) != 220 or set(sequences) != set(range(220)):
        raise AssertionError("Messages acquittés perdus ou dupliqués après panne")
    admin = KafkaAdminClient(bootstrap_servers=brokers, request_timeout_ms=10000)
    final = admin.describe_topics([args.topic])[0]
    admin.close()
    if final["partitions"][0]["leader"] == 1 or set(final["partitions"][0]["isr"]) != {101, 102}:
        raise AssertionError("Le leader n'a pas basculé sur les répliques prévues")
    report = {"event": "kafka_leader_failure_verified", "topic": args.topic, "finished_at_utc": now(),
              "replicas": 3, "min_insync_replicas": 2, "acks": "all", "producer_idempotence": True,
              "acknowledged_rows": 220, "read_rows": len(sequences), "unique_sequences": len(set(sequences)),
              "lost_acknowledged_rows": 0, "duplicate_rows": 0, "initial_metadata": initial, "final_metadata": final,
              "injection": json.loads((control/"inject-now.json").read_text()),
              "acknowledgements": acknowledgements,
              "ack_latency_seconds": {"median": statistics.median(latencies), "max": max(latencies),
                                      "before_fault_max": max(latencies[:20]), "after_fault_max": max(latencies[20:])},
              "elapsed_seconds_including_operator_wait": time.monotonic()-started,
              "limitations": "single host, single ZooKeeper; isolated topic only; no global HA/RPO/RTO guarantee"}
    (control/"result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
