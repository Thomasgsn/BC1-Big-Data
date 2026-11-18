"""Écrire/relire un préfixe PaySim réel avec un runtime HDFS candidat isolé."""

import argparse
from collections import defaultdict
import csv
from decimal import Decimal
import hashlib
from itertools import islice
import json
from pathlib import Path

from rncp_bc1.transactions import ID_PATTERN

DATASET_SHA = "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--read-existing", action="store_true")
    parser.add_argument("--csv", type=Path, default=Path("/project/data/raw/PS_20174392719_1491204439457_log.csv"))
    args = parser.parse_args()
    if not ID_PATTERN.fullmatch(args.run_id):
        parser.error("Identifiant invalide")
    digest = hashlib.sha256()
    with args.csv.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != DATASET_SHA:
        raise AssertionError("Empreinte PaySim différente de la source verrouillée")
    with args.csv.open(newline="") as stream:
        rows = [(index, row["type"], int(row["step"]), Decimal(row["amount"]))
                for index, row in enumerate(islice(csv.DictReader(stream), 1000), start=1)]
    if len(rows) != 1000:
        raise AssertionError("Préfixe incomplet")
    expected = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    for _, kind, _, amount in rows:
        expected[kind]["rows"] += 1
        expected[kind]["amount"] += amount
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-candidate-hdfs-probe")
             .config("spark.sql.session.timeZone", "UTC").config("spark.sql.shuffle.partitions", "2").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    try:
        path = "hdfs://namenode:8020/bc1/runtime-check/"+args.run_id
        original = spark.createDataFrame(rows, "source_row long, type string, step int, amount decimal(18,2)")
        if not args.read_existing:
            original.write.mode("error").parquet(path)
        actual = spark.read.parquet(path)
        if actual.schema["amount"].dataType.simpleString() != "decimal(18,2)":
            raise AssertionError("Type décimal non préservé")
        if original.exceptAll(actual).limit(1).count() or actual.exceptAll(original).limit(1).count():
            raise AssertionError("Contenu HDFS différent du préfixe PaySim")
        observed = {row["type"]: {"rows": row["rows"], "amount": row["amount"]}
                    for row in actual.groupBy("type").agg(F.count("*").alias("rows"), F.sum("amount").alias("amount")).collect()}
        if observed != expected:
            raise AssertionError("Comptages ou sommes différents du CSV")
        print(json.dumps({"event": "candidate_hdfs_verified", "rows": len(rows), "dataset_sha256": DATASET_SHA,
                          "path": path, "read_existing": args.read_existing, "multiset_and_decimal_sums_equal": True,
                          "spark_version": spark.version,
                          "client_hadoop_version": spark.sparkContext._jvm.org.apache.hadoop.util.VersionInfo.getVersion(),
                          "scope": "local Spark driver, real HDFS servers and real PaySim prefix; not a whole-platform migration"}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
