"""Copie analytique partitionnée par type, égalité multiensemble et benchmark de lecture contrôlé."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import statistics
import time


def scan_metrics(plan):
    result = []
    if plan.getClass().getSimpleName() == "FileSourceScanExec":
        items, values = plan.metrics().iterator(), {}
        while items.hasNext():
            item = items.next()
            values[str(item._1())] = item._2().value()
        result.append(values)
    children = plan.children().iterator()
    while children.hasNext():
        result.extend(scan_metrics(children.next()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="training-sample64-seed42")
    parser.add_argument("--layout-version", required=True)
    args = parser.parse_args()
    from rncp_bc1.transactions import ID_PATTERN
    if not all(ID_PATTERN.fullmatch(x) for x in [args.run_id, args.layout_version]):
        parser.error("Identifiants invalides")
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-parquet-optimization")
             .config("spark.sql.session.timeZone", "UTC").config("spark.sql.shuffle.partitions", "4")
             .config("spark.sql.adaptive.enabled", "false").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    root = f"hdfs://namenode:8020/bc1/{args.run_id}"
    destination = root+"/optimized/"+args.layout_version
    try:
        original = spark.read.parquet(root+"/curated")
        count = original.count()
        begin = time.monotonic()
        original.repartition(5, "type").write.mode("error").partitionBy("type").parquet(destination)
        write_seconds = time.monotonic()-begin
        restored = spark.read.parquet(destination).select(*original.columns)
        if restored.count() != count or original.exceptAll(restored).limit(1).count() or restored.exceptAll(original).limit(1).count():
            raise AssertionError("Copie optimisée différente de la source, y compris doublons et colonnes")
        reports = {}
        digests = set()
        for name, path in [("curated_initial", root+"/curated"), ("partitioned_by_type", destination)]:
            spark.catalog.clearCache()
            timings = []
            for repeat in range(4):
                begin = time.monotonic()
                data = spark.read.parquet(path)
                query = (data.filter((F.col("type") == "TRANSFER") & (F.col("step") > 355))
                         .agg(F.countDistinct("transaction_id").alias("transactions"), F.sum("amount").alias("amount")))
                rows = [row.asDict() for row in query.collect()]
                elapsed = time.monotonic()-begin
                digests.add(hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest())
                if repeat:
                    timings.append(elapsed)
            plan = query._jdf.queryExecution().executedPlan()
            reports[name] = {"query_seconds": timings, "median_seconds": statistics.median(timings),
                             "result": rows, "scan_metrics": scan_metrics(plan), "physical_plan": plan.toString(),
                             "total_input_files_before_filter": len(data.inputFiles())}
        if len(digests) != 1:
            raise AssertionError("Résultat de requête modifié par le partitionnement")
        report = {"event": "parquet_layout_verified", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "run_id": args.run_id, "layout_version": args.layout_version, "rows": count,
                  "all_columns_multiset_equality": True, "write_seconds": write_seconds, "comparison": reports,
                  "result_sha256": next(iter(digests)), "original_untouched": True,
                  "limitations": "small sample; OS cache not flushed, first read excluded per layout; no global speedup claim"}
        spark.createDataFrame([(json.dumps(report, default=str),)], ["value"]).coalesce(1).write.mode("error").text(root+"/optimization-reports/"+args.layout_version)
        print(json.dumps(report, default=str))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
