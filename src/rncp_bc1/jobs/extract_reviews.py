"""Snapshot SQL immuable vers HDFS et contrôle des références transactionnelles.

Sur ce petit registre, une lecture complète évite de perdre une transaction SQL
validée tardivement derrière un curseur temporel. Ce n'est pas une CDC incrémentale.
"""

import argparse
import json
import os

from rncp_bc1.transactions import ID_PATTERN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--transaction-run", required=True)
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    args = parser.parse_args()
    if not all(ID_PATTERN.fullmatch(value) for value in [args.snapshot_id, args.transaction_run]):
        parser.error("Identifiant de snapshot/rejeu invalide")
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-sql-reviews-extraction").config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "2").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    frame = None
    try:
        query = """SELECT d.decision_id::text, d.case_id::text, c.transaction_id::text, d.analyst_id,
          d.outcome, d.reason, d.version, d.origin, d.created_at
          FROM analyst_decision d JOIN investigation_case c ON c.case_id=d.case_id"""
        frame = (spark.read.format("jdbc").option("url", "jdbc:postgresql://postgres:5432/bc1")
                 .option("query", query).option("driver", "org.postgresql.Driver").option("user", "bc1app")
                 .option("password", os.environ["POSTGRES_APP_PASSWORD"]).load()
                 .withColumn("source_system", F.lit("postgresql_analyst_reviews"))
                 .withColumn("snapshot_id", F.lit(args.snapshot_id)).cache())
        count = frame.count()
        if not 1 <= count <= 100000:
            raise ValueError("Snapshot vide ou dépassant 100 000 revues ; revoir la stratégie d'extraction.")
        if frame.select("decision_id").distinct().count() != count:
            raise AssertionError("Identifiants de décision dupliqués.")
        transactions = spark.read.parquet(args.base.rstrip("/")+"/"+args.transaction_run+"/curated").select("transaction_id").distinct()
        if frame.join(transactions, "transaction_id", "left_anti").limit(1).count():
            raise AssertionError("Une décision référence une transaction absente du rejeu HDFS choisi.")
        root = args.base.rstrip("/")+"/reviews/"+args.snapshot_id
        frame.write.mode("error").parquet(root+"/raw")
        curated = frame.dropDuplicates(["decision_id"]).withColumn("row_sha256", F.sha2(F.to_json(F.struct(*frame.columns)), 256))
        curated.write.mode("error").parquet(root+"/curated")
        reread = spark.read.parquet(root+"/curated")
        if reread.count() != count:
            raise AssertionError("Le nombre de revues relues diffère de SQL.")
        origins = {x["origin"]: x["count"] for x in reread.groupBy("origin").count().collect()}
        report = {"event": "sql_reviews_integrated", "snapshot_id": args.snapshot_id, "rows": count,
                  "origins": origins, "references_validated_against": args.transaction_run,
                  "strategy": "complete_immutable_snapshot_not_cdc", "root": root}
        spark.createDataFrame([(json.dumps(report),)], ["value"]).coalesce(1).write.mode("error").text(root+"/report")
        print(json.dumps(report))
    finally:
        if frame is not None:
            frame.unpersist()
        spark.stop()


if __name__ == "__main__":
    main()
