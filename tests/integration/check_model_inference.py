"""Recharger les deux modèles réels, tester leurs limites et rapprocher Mongo.

Les fixtures limites sont artificielles et ne mesurent aucune qualité de détection.
Aucun entraînement, écriture métier ou ajustement du test temporel n'est effectué.
"""

import argparse
from decimal import Decimal
import json
import math
import os
from urllib.parse import quote

from rncp_bc1.dataset import TYPES
from rncp_bc1.transactions import ID_PATTERN, MONEY_LIMIT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--transaction-run", required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    args = parser.parse_args()
    if not all(ID_PATTERN.fullmatch(value) for value in
               [args.training_run, args.model_version, args.transaction_run]):
        parser.error("Identifiant invalide")
    if not 1 <= args.expected_rows <= 10000:
        parser.error("Contrôle borné à 1–10 000 lignes")
    from pyspark.ml import PipelineModel
    from pyspark.sql import SparkSession, functions as F
    from pyspark.sql.types import DecimalType, IntegerType, StringType, StructField, StructType
    from rncp_bc1.jobs.columns import score_column

    spark = (SparkSession.builder.appName("bc1-model-inference-check")
             .config("spark.sql.session.timeZone", "UTC").config("spark.sql.shuffle.partitions", "2")
             .config("spark.redaction.regex", "(?i)secret|password|token|connection.uri")
             .config("spark.redaction.string.regex", "mongodb://[^@]+@").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    try:
        root = args.base.rstrip("/")
        artifact = root+"/"+args.training_run+"/models/"+args.model_version
        report = json.loads(spark.read.text(artifact+"/report").first()["value"])
        schema = StructType([StructField("fixture_id", StringType(), False),
                             StructField("type", StringType(), False),
                             StructField("amount", DecimalType(18, 2), False),
                             StructField("step", IntegerType(), False)])
        rows = [(f"{kind}-{index}", kind, amount, step)
                for kind in sorted(TYPES)
                for index, (amount, step) in enumerate([
                    (Decimal("0.00"), 1), (Decimal("0.01"), 24),
                    (MONEY_LIMIT, 25), (Decimal("100.00"), 744)])]
        # Le pipeline sait encoder un type inédit, mais le contrat métier le rejette.
        # Ce cas teste la robustesse ML interne, pas l'autorisation d'ingérer ce type.
        rows.append(("unseen-type", "ARTIFICIAL_UNSEEN_TYPE", Decimal("1.00"), 1))
        fixtures = spark.createDataFrame(rows, schema)
        fixture_reports = {}
        selected = None
        for name in ["logistic_regression", "random_forest"]:
            model = PipelineModel.load(artifact+"/"+name)
            results = model.transform(fixtures).select("fixture_id", "features", "probability").collect()
            if len(results) != len(rows) or {row["fixture_id"] for row in results} != {row[0] for row in rows}:
                raise AssertionError("Une fixture a disparu pendant l'inférence")
            for row in results:
                features = list(row["features"])
                probabilities = list(row["probability"])
                if (len(features) != model.stages[-1].numFeatures
                        or not all(math.isfinite(float(value)) for value in features)
                        or len(probabilities) != 2
                        or not all(math.isfinite(float(value)) and 0 <= value <= 1 for value in probabilities)
                        or not math.isclose(sum(probabilities), 1, abs_tol=1e-12)):
                    raise AssertionError(f"Vecteur/score invalide pour {name}, {row['fixture_id']}")
            fixture_reports[name] = {"rows": len(results), "all_vectors_and_scores_finite": True,
                                     "feature_dimension": model.stages[-1].numFeatures}
            if name == report["selected"]:
                selected = model
        if selected is None:
            raise AssertionError("Modèle retenu absent des candidats sauvegardés")
        transactions = (spark.read.parquet(root+"/"+args.transaction_run+"/curated")
                        .select("transaction_id", "step", "type", "amount")
                        .limit(args.expected_rows+1))
        if transactions.count() != args.expected_rows:
            raise AssertionError("Effectif HDFS différent de la référence bornée")
        direct = selected.transform(transactions).select("transaction_id", score_column().alias("direct_score"))
        uri = "mongodb://bc1app:"+quote(os.environ["MONGO_APP_PASSWORD"], safe="")+"@mongo:27017/fraud?authSource=fraud"
        stored = (spark.read.format("mongodb").option("connection.uri", uri).option("database", "fraud")
                  .option("collection", "fraud_scores").load()
                  .filter((F.col("model_version") == args.training_run+":"+args.model_version)
                          & (F.col("run_id") == args.transaction_run))
                  .select("transaction_id", "score", "threshold", "is_alert"))
        if stored.count() != args.expected_rows or stored.select("transaction_id").distinct().count() != args.expected_rows:
            raise AssertionError("Effectif ou unicité Mongo différents de la référence")
        joined = direct.join(stored, "transaction_id", "full")
        if joined.filter(F.col("direct_score").isNull() | F.col("score").isNull()).limit(1).count():
            raise AssertionError("Identifiants absents dans une source")
        max_difference = joined.agg(F.max(F.abs(F.col("score")-F.col("direct_score")))).first()[0]
        if max_difference is None or not math.isfinite(max_difference) or max_difference > 1e-12:
            raise AssertionError("Scores Mongo différents de l'inférence directe")
        invalid = joined.filter(F.col("threshold").isNull() | F.col("is_alert").isNull()
                                | (F.col("threshold") != F.lit(report["threshold"]))
                                | (F.col("is_alert") != (F.col("direct_score") >= F.lit(report["threshold"]))))
        if invalid.limit(1).count():
            raise AssertionError("Seuil ou décision publiés incohérents")
        print(json.dumps({"event": "model_inference_verified", "training_run": args.training_run,
                          "model_version": args.model_version, "transaction_run": args.transaction_run,
                          "artificial_boundary_fixtures": fixture_reports,
                          "fixture_scope": "five valid types, zero/cent/max amount, day boundary/future hour; separate unseen internal type",
                          "real_rows_compared": args.expected_rows, "max_score_absolute_difference": max_difference,
                          "published_threshold_and_alerts_match": True, "labels_or_balances_in_input": False,
                          "writes_or_retraining": False}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
