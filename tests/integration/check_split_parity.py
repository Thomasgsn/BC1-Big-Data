"""Compare le découpage par effectifs de step au découpage enregistré par un entraînement antérieur."""

import json
import sys

from pyspark.sql import SparkSession

from rncp_bc1.jobs.train import step_quantiles

root, expected = sys.argv[1], [int(sys.argv[2]), int(sys.argv[3])]
spark = SparkSession.builder.appName("bc1-split-parity").config("spark.sql.shuffle.partitions", "2").getOrCreate()
try:
    data = spark.read.parquet(root + "/curated").select("transaction_id", "step").dropDuplicates(["transaction_id"])
    counted = step_quantiles([(int(r["step"]), int(r["count"])) for r in data.groupBy("step").count().collect()], [0.6, 0.8])
    print(json.dumps({"event": "split_parity_checked", "root": root, "recorded_split": expected, "step_counts": counted,
                      "identical": expected == counted}))
    if expected != counted:
        raise SystemExit(1)
finally:
    spark.stop()
