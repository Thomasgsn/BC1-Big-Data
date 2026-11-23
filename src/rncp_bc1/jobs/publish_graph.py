"""Publier un graphe financier et des agrégats HDFS vers MongoDB."""

import argparse
import json
import os

from rncp_bc1.transactions import ID_PATTERN
from rncp_bc1.security import mongo_spark_uri


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--step-from", type=int, default=1)
    parser.add_argument("--step-to", required=True, type=int)
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    args = parser.parse_args()
    if not ID_PATTERN.fullmatch(args.run_id) or args.step_from < 1 or args.step_to < args.step_from:
        parser.error("Identifiant ou fenêtre temporelle invalide")
    password = os.environ.get("MONGO_APP_PASSWORD")
    if not password:
        parser.error("MONGO_APP_PASSWORD requis dans l'environnement, jamais en argument")
    uri = mongo_spark_uri(password)
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-data-lab").config("spark.sql.shuffle.partitions", "2")
             .config("spark.redaction.regex", "(?i)secret|password|token|access.key|connection.uri")
             .config("spark.redaction.string.regex", "mongodb://[^@]+@").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    snapshot = f"{args.run_id}-steps-{args.step_from}-{args.step_to}"
    frames = []
    try:
        data = (spark.read.parquet(args.base.rstrip("/")+"/"+args.run_id+"/curated")
                .filter(F.col("step").between(args.step_from, args.step_to)).dropDuplicates(["transaction_id"]).cache())
        frames.append(data)
        source_count = data.count()
        if not source_count:
            raise ValueError("Aucune transaction dans cette fenêtre.")
        edges = data.groupBy("source", "target").agg(F.count("*").alias("transaction_count"), F.sum("amount").alias("total_amount"))
        edges = (edges.withColumn("snapshot_id", F.lit(snapshot))
                 .withColumn("_id", F.sha2(F.concat_ws("|", "snapshot_id", "source", "target"), 256)).cache())
        frames.append(edges)
        edge_count = edges.count()
        if edge_count > 50000:
            raise ValueError("Plus de 50 000 arêtes ; réduire la fenêtre au lieu de tronquer silencieusement.")
        nodes = (edges.select(F.col("source").alias("node_id")).union(edges.select(F.col("target").alias("node_id")))
                 .distinct().withColumn("snapshot_id", F.lit(snapshot))
                 .withColumn("_id", F.sha2(F.concat_ws("|", "snapshot_id", "node_id"), 256)).cache())
        frames.append(nodes)
        node_count = nodes.count()
        metrics = data.groupBy("step", "type").agg(F.count("*").alias("transaction_count"), F.sum("amount").alias("total_amount"))
        metrics = metrics.withColumn("snapshot_id", F.lit(snapshot)).withColumn("_id", F.sha2(F.concat_ws("|", "snapshot_id", "step", "type"), 256))

        def write(frame, collection):
            (frame.write.format("mongodb").mode("append").option("connection.uri", uri).option("database", "fraud")
             .option("collection", collection).option("operationType", "replace").option("idFieldList", "_id")
             .option("upsertDocument", "true").save())

        write(edges, "graph_edges")
        write(nodes, "graph_nodes")
        write(metrics, "transaction_metrics")
        metadata = {"_id": snapshot, "snapshot_id": snapshot, "run_id": args.run_id,
                    "step_from": args.step_from, "step_to": args.step_to,
                    "transactions": source_count, "nodes": node_count, "edges": edge_count, "status": "complete"}
        write(spark.createDataFrame([metadata]), "graph_snapshots")
        print(json.dumps({"event": "data_lab_published", **metadata}))
    finally:
        for frame in frames:
            frame.unpersist()
        spark.stop()


if __name__ == "__main__":
    main()
