"""Empreintes de scores des modèles sauvegardés pour comparer deux runtimes HDFS.

Lecture seule : n'entraîne aucun modèle et ne modifie pas le test final.
"""

import argparse
import hashlib
import json
import math

from rncp_bc1.transactions import ID_PATTERN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--transaction-run", required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    args = parser.parse_args()
    if not all(ID_PATTERN.fullmatch(value) for value in
               [args.training_run, args.model_version, args.transaction_run]):
        parser.error("Identifiant invalide")
    if not 1 <= args.expected_rows <= 10000:
        parser.error("Lecture bornée à 1–10 000 transactions")
    from pyspark.ml import PipelineModel
    from pyspark.sql import SparkSession
    from rncp_bc1.jobs.columns import score_column
    spark = SparkSession.builder.appName("bc1-hdfs-model-reload").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        root = "hdfs://namenode:8020/bc1"
        artifact = root+"/"+args.training_run+"/models/"+args.model_version
        report_text = spark.read.text(artifact+"/report").first()["value"]
        report = json.loads(report_text)
        data = (spark.read.parquet(root+"/"+args.transaction_run+"/curated")
                .select("transaction_id", "step", "type", "amount").limit(args.expected_rows+1))
        if data.count() != args.expected_rows or data.select("transaction_id").distinct().count() != args.expected_rows:
            raise AssertionError("Effectif ou unicité du jeu d'inférence incorrects")
        trained_rows = spark.read.parquet(root+"/"+args.training_run+"/curated").count()
        if trained_rows != sum(sum(counts.values()) for counts in report["split"]["classes"].values()):
            raise AssertionError("Données d'entraînement absentes ou incomplètes")
        results = {}
        for name in ["logistic_regression", "random_forest"]:
            model = PipelineModel.load(artifact+"/"+name)
            predictions = model.transform(data).select("transaction_id", score_column().alias("score")).collect()
            if not all(math.isfinite(row["score"]) and 0 <= row["score"] <= 1 for row in predictions):
                raise AssertionError("Score non fini ou hors intervalle")
            canonical = "\n".join(f"{row['transaction_id']}:{row['score']:.17g}" for row in sorted(predictions, key=lambda x: x["transaction_id"]))
            results[name] = {"rows": len(predictions), "scores_sha256": hashlib.sha256(canonical.encode()).hexdigest()}
            if name == report["selected"]:
                results[name]["alerts"] = sum(row["score"] >= report["threshold"] for row in predictions)
        print(json.dumps({"event": "hdfs_models_reloaded", "models": results, "training_rows_read": trained_rows,
                          "training_report_text_sha256": hashlib.sha256(report_text.encode()).hexdigest(),
                          "selected": report["selected"], "threshold": report["threshold"],
                          "scope": "Read-only artifacts and inference scores; no training or checkpoint resume."}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
