"""Même agrégation sur les mêmes transactions, trois répétitions ; vérifier les exécutants réels."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import statistics
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="training-sample64-seed42")
    parser.add_argument("--expected-executors", type=int, required=True)
    args = parser.parse_args()
    from rncp_bc1.transactions import ID_PATTERN
    if not ID_PATTERN.fullmatch(args.run_id) or args.expected_executors not in [1, 2]:
        parser.error("Rejeu ou nombre d'exécuteurs invalide")
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-scalability-benchmark")
             .config("spark.sql.shuffle.partitions", "32").config("spark.sql.adaptive.enabled", "false").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    frame = None
    try:
        begin = time.monotonic()
        frame = spark.read.parquet(f"hdfs://namenode:8020/bc1/{args.run_id}/curated").select("step", "type", "amount", "transaction_id").cache()
        count = frame.count()
        load_seconds = time.monotonic()-begin
        app_id = spark.sparkContext.applicationId
        # Le driver annonce et lie son IP Docker propre, pas l'interface loopback.
        with urllib.request.urlopen(f"{spark.sparkContext.uiWebUrl}/api/v1/applications/{app_id}/executors", timeout=10) as response:
            executors = [x for x in json.load(response) if x["id"] != "driver" and x["isActive"]]
        if len(executors) != args.expected_executors:
            raise AssertionError("Configuration réelle des exécuteurs différente de l'expérience prévue")
        def execute():
            # Nouvelle QueryExecution à chaque répétition : ne pas réutiliser les échanges
            # matérialisés par le même objet SparkPlan après le premier collect().
            query = (frame.withColumn("hash_probe", F.sha2("transaction_id", 256)).groupBy("step", "type")
                     .agg(F.countDistinct("transaction_id").alias("transactions"), F.sum("amount").alias("amount"),
                          F.min("hash_probe").alias("min_hash")))
            rows = [row.asDict() for row in query.collect()]
            rows.sort(key=lambda x: (x["step"], x["type"]))
            if sum(x["transactions"] for x in rows) != count:
                raise AssertionError("Perte ou doublons dans l'agrégation de charge")
            return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest(), len(rows)
        expected_digest, groups = execute()  # échauffement explicite non inclus dans les trois mesures.
        timings = []
        for _ in range(3):
            begin = time.monotonic()
            digest, _ = execute()
            timings.append(time.monotonic()-begin)
            if digest != expected_digest:
                raise AssertionError("Résultats de charge non déterministes")
        print(json.dumps({"event": "spark_compute_benchmark", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": args.run_id, "rows": count, "groups": groups, "result_sha256": expected_digest,
            "executor_count": len(executors), "executor_cores": [x["totalCores"] for x in executors],
            "executor_memory": "1g", "shuffle_partitions": 32, "adaptive_query_execution": False,
            "fresh_query_execution_each_repeat": True,
            "load_and_cache_seconds": load_seconds, "query_seconds": timings, "median_seconds": statistics.median(timings),
            "limitations": "small cached sample; single-host worker scaling, no host fault tolerance; warmup excluded"}))
    finally:
        if frame is not None:
            frame.unpersist()
        spark.stop()


if __name__ == "__main__":
    main()
