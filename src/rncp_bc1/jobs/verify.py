"""Vérifier le rejeu HDFS par rapport à une référence calculée sur le CSV source."""

import argparse
from collections import Counter
import csv
from decimal import Decimal
import json
from pathlib import Path
import re

from rncp_bc1.dataset import sha256_file
from rncp_bc1.transactions import ID_PATTERN


def expected(csv_path: Path, limit: int):
    counts = Counter()
    totals = Counter()
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        for position, row in enumerate(csv.DictReader(stream), 1):
            if position > limit:
                break
            counts[row["type"]] += 1
            totals[row["type"]] += Decimal(row["amount"])
    if sum(counts.values()) != limit:
        raise ValueError("La source contient moins de lignes que la limite attendue.")
    return {key: {"count": counts[key], "amount": str(totals[key])} for key in sorted(counts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--expected-raw-rows", type=int, help="Inclure les doublons volontairement rejoués dans le contrôle raw")
    parser.add_argument("--expected-quarantine-rows", type=int, default=0)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    args = parser.parse_args()
    if args.limit < 1 or not ID_PATTERN.fullmatch(args.run_id):
        parser.error("Limite ou run-id invalide")
    reference = expected(args.csv, args.limit)
    from pyspark.sql import SparkSession, functions as F
    spark = SparkSession.builder.appName("bc1-verification").config("spark.sql.session.timeZone", "UTC").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        root = args.base.rstrip("/") + "/" + args.run_id
        frame = spark.read.parquet(root + "/curated")
        observed = {row["type"]: {"count": row["count"], "amount": str(row["amount"])}
                    for row in frame.groupBy("type").agg(F.count("*").alias("count"), F.sum("amount").alias("amount")).collect()}
        count = frame.count()
        distinct = frame.select("transaction_id").distinct().count()
        if count != args.limit or distinct != count:
            raise AssertionError(f"Comptage/identités incohérents : {count=}, {distinct=}, limite={args.limit}")
        if set(observed) != set(reference):
            raise AssertionError("Types observés différents des types attendus.")
        for key in reference:
            if observed[key]["count"] != reference[key]["count"] or Decimal(observed[key]["amount"]) != Decimal(reference[key]["amount"]):
                raise AssertionError(f"Agrégation différente pour {key}.")
        bounds = frame.agg(F.min("source_row").alias("low"), F.max("source_row").alias("high"),
                           F.countDistinct("source_row").alias("distinct")).first()
        if (bounds["low"], bounds["high"], bounds["distinct"]) != (1, args.limit, args.limit):
            raise AssertionError("Les positions source ne correspondent pas au rejeu attendu.")
        digest = sha256_file(args.csv)
        expected_id = F.sha2(F.concat(F.lit(digest+":"), F.col("source_row").cast("string")), 256)
        if frame.filter((F.col("transaction_id") != expected_id) | (F.col("replay_run_id") != args.run_id)
                        | (F.col("dataset_id") != "paysim-v2:"+digest)).limit(1).count():
            raise AssertionError("Provenance ou identité transactionnelle incohérente.")
        raw_count = spark.read.parquet(root + "/raw").count()
        expected_raw = args.expected_raw_rows if args.expected_raw_rows is not None else args.limit
        if raw_count != expected_raw:
            raise AssertionError(f"Nombre de messages raw inattendu : {raw_count} au lieu de {expected_raw}.")
        rejected = spark.read.parquet(root + "/quarantine")
        rejected_count = rejected.count()
        if rejected_count != args.expected_quarantine_rows:
            raise AssertionError(f"Nombre de rejets inattendu : {rejected_count} au lieu de {args.expected_quarantine_rows}.")
        rejection_reasons = {row["rejection_reason"]: row["count"]
                             for row in rejected.groupBy("rejection_reason").count().collect()}
        path = spark._jvm.org.apache.hadoop.fs.Path(root + "/metrics")
        filesystem = path.getFileSystem(spark._jsc.hadoopConfiguration())
        batches = [int(str(s.getPath().getName()).split("=", 1)[1]) for s in filesystem.listStatus(path)
                   if re.fullmatch(r"batch_id=\d+", str(s.getPath().getName()))]
        if not batches:
            raise AssertionError("Aucune photographie de métriques disponible.")
        metric_frame = spark.read.parquet(root + f"/metrics/batch_id={max(batches)}")
        metric_rows = metric_frame.groupBy("type").agg(F.sum("transaction_count").alias("count"),
                                                      F.sum("total_amount").alias("amount")).collect()
        for row in metric_rows:
            reference_row = reference.get(row["type"])
            if not reference_row or row["count"] != reference_row["count"] or row["amount"] != Decimal(reference_row["amount"]):
                raise AssertionError("Les métriques stream diffèrent de la référence CSV.")
        if {row["type"] for row in metric_rows} != set(reference):
            raise AssertionError("Types manquants dans les métriques stream.")
        latency = frame.select((F.col("ingested_at").cast("double")-F.col("emitted_at").cast("double")).alias("seconds"))
        latency_stats = latency.agg(F.min("seconds").alias("min"), F.max("seconds").alias("max"),
                                    F.percentile_approx("seconds", 0.95).alias("p95")).first().asDict()
        print(json.dumps({"event": "hdfs_verified", "run_id": args.run_id, "rows": count, "raw_rows": raw_count,
                          "quarantine_rows": rejected_count, "rejection_reasons": rejection_reasons,
                          "dataset_sha256": digest, "observed": observed, "expected": reference,
                          "latency_seconds": latency_stats,
                          "latency_definition": "emitted_at to Spark batch ingested_at; excludes sink commit/read visibility",
                          "scope": "rejeu borné ; pas benchmark de production"}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
