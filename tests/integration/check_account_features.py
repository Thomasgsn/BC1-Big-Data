"""Vérifie dans Spark que l'historique destinataire n'utilise ni le même step ni le futur."""

import json
import math

from pyspark.sql import SparkSession

from rncp_bc1.jobs.account_features import add_destination_history

spark = SparkSession.builder.appName("bc1-account-features-check").config("spark.sql.shuffle.partitions", "2").getOrCreate()
try:
    rows = [("t1", "D1", 1, 100.0), ("t2", "D1", 1, 300.0), ("t3", "D1", 5, 50.0),
            ("t4", "D1", 40, 1000.0), ("t5", "D2", 5, 10.0)]
    frame = spark.createDataFrame(rows, ["transaction_id", "target", "step", "amount"])
    got = {r["transaction_id"]: r.asDict() for r in add_destination_history(frame).collect()}
    expected = {
        "t1": (0, 0, 0.0, 1.0), "t2": (0, 0, 0.0, 1.0),
        "t3": (2, 2, math.log1p(50) - math.log1p(200), 0.0),
        "t4": (3, 0, math.log1p(1000) - math.log1p(450 / 3), 0.0),
        "t5": (0, 0, 0.0, 1.0)}
    failures = []
    for key, (count, day, deviation, first) in expected.items():
        row = got[key]
        values = (row["dest_prior_count_log"], row["dest_prior_24h_log"], row["amount_vs_dest_mean"], row["dest_first_seen"])
        wanted = (math.log1p(count), math.log1p(day), deviation, first)
        if any(abs(a - b) > 1e-9 for a, b in zip(values, wanted)):
            failures.append({"transaction_id": key, "got": values, "expected": wanted})
    print(json.dumps({"event": "account_features_checked", "rows": len(got), "failures": failures}))
    if failures:
        raise SystemExit(1)
finally:
    spark.stop()
