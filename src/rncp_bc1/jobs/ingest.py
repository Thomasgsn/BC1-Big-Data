"""Kafka → Parquet HDFS : brut, curated, quarantaine et métriques de rejeu."""

import argparse
import json
import time
import math

from rncp_bc1.dataset import DECIMAL_FIELDS, TYPES
from rncp_bc1.transactions import ID_PATTERN

PAYSIM_V2_SHA256 = "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"


def event_schema():
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, BooleanType
    payload = StructType([StructField("step", LongType()), StructField("type", StringType()),
                          StructField("nameOrig", StringType()), StructField("nameDest", StringType()),
                          *[StructField(key, StringType()) for key in DECIMAL_FIELDS],
                          StructField("isFraud", IntegerType()), StructField("isFlaggedFraud", IntegerType())])
    return StructType([StructField("schema_version", IntegerType()), StructField("dataset_id", StringType()),
                       StructField("source_row", LongType()), StructField("transaction_id", StringType()),
                       StructField("replay_run_id", StringType()), StructField("event_time", StringType()),
                       StructField("emitted_at", StringType()), StructField("event_time_synthetic", BooleanType()),
                       StructField("payload", payload)])


def classified(source, run_id, dataset_sha256=PAYSIM_V2_SHA256):
    from pyspark.sql import functions as F
    from pyspark.sql.types import DecimalType
    decoded = source.select(F.col("value").cast("string").alias("raw_json"),
                            F.col("key").cast("string").alias("kafka_key"), "topic", "partition", "offset",
                            F.col("timestamp").alias("kafka_timestamp"))
    parsed = decoded.withColumn("event", F.from_json("raw_json", event_schema()))
    parsed = parsed.select("raw_json", "kafka_key", "topic", "partition", "offset", "kafka_timestamp", "event.*")
    parsed = parsed.filter((F.col("replay_run_id") == run_id) | F.col("replay_run_id").isNull())
    checks = {
        "schema_version": F.col("schema_version") == 1,
        "dataset_id": F.col("dataset_id") == "paysim-v2:"+dataset_sha256,
        "source_row": F.col("source_row") > 0,
        "transaction_id": F.col("transaction_id").rlike(r"^[0-9a-f]{64}$"),
        "run_id": F.col("replay_run_id") == run_id,
        "synthetic_time": F.col("event_time_synthetic") == True,
        "step": F.col("payload.step") > 0,
        "type": F.col("payload.type").isin(sorted(TYPES)),
        "origin": F.col("payload.nameOrig").rlike(r"^[a-zA-Z0-9]{1,128}$"),
        "destination": F.col("payload.nameDest").rlike(r"^[a-zA-Z0-9]{1,128}$"),
        "label": F.col("payload.isFraud").isin(0, 1),
        "historical_flag": F.col("payload.isFlaggedFraud").isin(0, 1),
    }
    checks["identity"] = F.col("transaction_id") == F.sha2(F.concat(F.lit(dataset_sha256+":"), F.col("source_row").cast("string")), 256)
    for key in DECIMAL_FIELDS:
        checks[key] = F.col(f"payload.{key}").rlike(r"^[0-9]{1,16}(\.[0-9]{1,2})?$")
    for key in ["event_time", "emitted_at"]:
        checks[key] = F.to_timestamp(key).isNotNull() & F.col(key).rlike(r"(Z|\+00:00)$")
    errors = [F.when(~F.coalesce(condition, F.lit(False)), F.lit(name)) for name, condition in checks.items()]
    parsed = parsed.withColumn("rejection_reason", F.concat_ws(",", *errors))
    valid = parsed.filter(F.col("rejection_reason") == "").select(
        "schema_version", "dataset_id", "source_row", "transaction_id", "replay_run_id", "event_time_synthetic",
        F.to_timestamp("event_time").alias("event_time"), F.to_timestamp("emitted_at").alias("emitted_at"),
        F.col("payload.step").alias("step"), F.col("payload.type").alias("type"),
        F.col("payload.nameOrig").alias("source"), F.col("payload.nameDest").alias("target"),
        *[F.col(f"payload.{key}").cast(DecimalType(18, 2)).alias(key) for key in DECIMAL_FIELDS],
        F.col("payload.isFraud").alias("isFraud"), F.col("payload.isFlaggedFraud").alias("isFlaggedFraud"),
        "topic", "partition", "offset", F.current_timestamp().alias("ingested_at"))
    return parsed, valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bootstrap-servers", default="kafka:9092")
    parser.add_argument("--topic", default="transactions.v1")
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    parser.add_argument("--once", action="store_true", help="Traiter les offsets disponibles puis terminer")
    parser.add_argument("--starting-offsets", choices=["earliest", "latest"], default="earliest",
                        help="Seulement au premier démarrage ; un checkpoint existant fait autorité")
    parser.add_argument("--duration-seconds", type=int, default=0,
                        help="Arrêter proprement un flux permanent après cette durée (0 : sans limite)")
    parser.add_argument("--observe-visible", action="store_true",
                        help="Mesurer la première lecture Parquet validée ; flux borné, 10 000 identités maximum")
    args = parser.parse_args()
    if not ID_PATTERN.fullmatch(args.run_id):
        parser.error("run-id invalide")
    if args.duration_seconds < 0 or (args.once and args.duration_seconds):
        parser.error("Durée positive réservée au mode permanent")
    if args.observe_visible and not args.duration_seconds:
        parser.error("L'observation nécessite un flux permanent borné par --duration-seconds")
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-ingestion").config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "2")
             .config("spark.sql.streaming.stateStore.providerClass", "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider")
             .config("spark.sql.streaming.stateStore.rocksdb.boundedMemoryUsage", "true")
             .config("spark.sql.streaming.stateStore.rocksdb.maxMemoryUsageMB", "256").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    root = args.base.rstrip("/") + "/" + args.run_id
    queries = []
    try:
        from rncp_bc1.streaming_state import guard_streaming_state
        from rncp_bc1.security import kafka_stream_options
        guard_streaming_state(spark, root)
        source = (spark.readStream.format("kafka").option("kafka.bootstrap.servers", args.bootstrap_servers)
                  .options(**kafka_stream_options())
                  .option("subscribe", args.topic).option("startingOffsets", args.starting_offsets)
                  .option("failOnDataLoss", "true").option("maxOffsetsPerTrigger", "10000").load())
        parsed, valid = classified(source, args.run_id)
        # Déduplication durable sur tout le rejeu fini, sans expiration de l'identité.
        # L'état croît avec les transactions uniques : ce choix n'est pas un service infini.
        unique = valid.dropDuplicates(["transaction_id"])
        trigger = {"availableNow": True} if args.once else {"processingTime": "5 seconds"}
        for name, frame in [
            ("raw", parsed.select("raw_json", "topic", "partition", "offset", "kafka_timestamp")),
            ("curated", unique),
            ("quarantine", parsed.filter(F.col("rejection_reason") != "").select(
                "raw_json", "topic", "partition", "offset", "rejection_reason")),
        ]:
            # Créer les dossiers permet à la source métriques d'être attachée avant le premier fichier.
            path = spark._jvm.org.apache.hadoop.fs.Path(root + "/" + name)
            path.getFileSystem(spark._jsc.hadoopConfiguration()).mkdirs(path)
            query = (frame.writeStream.format("parquet").outputMode("append")
                     .option("path", root + "/" + name).option("checkpointLocation", root + "/checkpoints/" + name)
                     .queryName("bc1_"+name).trigger(**trigger).start())
            queries.append(query)
        if args.once:
            # Le snapshot availableNow des métriques doit voir tous les fichiers curated.
            for query in queries:
                query.awaitTermination()
        curated = spark.readStream.schema(unique.schema).parquet(root + "/curated")
        metrics = curated.groupBy(F.window("emitted_at", "1 minute"), "type").agg(
            F.count("*").alias("transaction_count"), F.sum("amount").alias("total_amount"))

        def snapshot(batch, batch_id):
            # Une photographie complète par batch, réécrite à la même clé lors d'une reprise.
            batch.write.mode("overwrite").parquet(root + f"/metrics/batch_id={batch_id}")

        metric_query = (metrics.writeStream.outputMode("complete").foreachBatch(snapshot)
                        .option("checkpointLocation", root + "/checkpoints/metrics")
                        .queryName("bc1_metrics").trigger(**trigger).start())
        queries.append(metric_query)
        if args.once:
            metric_query.awaitTermination()
        else:
            deadline = time.monotonic()+90
            while not all(q.lastProgress is not None for q in queries[:3]):
                if any(q.exception() is not None for q in queries):
                    raise RuntimeError("Une requête streaming a échoué avant disponibilité")
                if time.monotonic() >= deadline:
                    raise TimeoutError("Initialisation des offsets non confirmée sous 90 secondes")
                time.sleep(1)
            print(json.dumps({"event": "stream_ready", "run_id": args.run_id,
                              "starting_offsets": args.starting_offsets}), flush=True)
            if args.duration_seconds:
                if args.observe_visible:
                    deadline = time.monotonic() + args.duration_seconds
                    seen = {}
                    polls = 0
                    while time.monotonic() < deadline:
                        if any(q.exception() is not None for q in queries):
                            raise RuntimeError("Échec streaming pendant l'observation de visibilité")
                        rows = (spark.read.schema(unique.schema).parquet(root + "/curated")
                                .select("transaction_id", F.col("emitted_at").cast("double").alias("emitted"))
                                .limit(10001).collect())
                        observed_at = time.time()
                        polls += 1
                        if len(rows) > 10000:
                            raise RuntimeError("Observation limitée à 10 000 identités")
                        for row in rows:
                            if row.emitted is None or observed_at < row.emitted:
                                raise ValueError("Horodatage non comparable à l'horloge d'observation")
                            seen.setdefault(row.transaction_id, observed_at - row.emitted)
                        time.sleep(min(5, max(0, deadline - time.monotonic())))
                    values = sorted(seen.values())
                    print(json.dumps({"event": "committed_visibility_observed", "run_id": args.run_id,
                                      "rows": len(values), "polls": polls,
                                      "seconds": {"min": values[0] if values else None,
                                                  "p95": values[math.ceil(.95 * len(values)) - 1] if values else None,
                                                  "max": values[-1] if values else None},
                                      "definition": "emitted_at to completed first successful Parquet reader collect; upper bound includes polling, reader and observer overhead",
                                      "poll_interval_seconds": 5, "scope": "Bounded 10000-row same-host observation; no production latency guarantee"}), flush=True)
                else:
                    spark.streams.awaitAnyTermination(args.duration_seconds)
            else:
                spark.streams.awaitAnyTermination()
        print(json.dumps({"event": "ingestion_completed", "run_id": args.run_id, "root": root,
                          "queries": [{"name": q.name, "active": q.isActive,
                                       "last_progress": q.lastProgress} for q in queries]}))
    finally:
        for query in queries:
            if query.isActive:
                query.stop()
        spark.stop()


if __name__ == "__main__":
    main()
