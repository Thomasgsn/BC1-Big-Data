"""Scorer des transactions sans labels ni soldes et publier les alertes MongoDB."""

import argparse
import json
import os

from rncp_bc1.transactions import ID_PATTERN
from rncp_bc1.security import mongo_spark_uri


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--training-run", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    args = parser.parse_args()
    if not all(ID_PATTERN.fullmatch(x) for x in [args.run_id, args.training_run, args.model_version]):
        parser.error("Identifiant invalide")
    if not os.environ.get("MONGO_APP_PASSWORD"):
        parser.error("MONGO_APP_PASSWORD requis")
    from pyspark.sql import SparkSession, functions as F
    from pyspark.ml import PipelineModel
    from rncp_bc1.jobs.columns import score_column, vector_array_column
    spark = (SparkSession.builder.appName("bc1-model-scoring").config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "2")
             .config("spark.redaction.regex", "(?i)secret|password|token|access.key|connection.uri")
             .config("spark.redaction.string.regex", "mongodb://[^@]+@").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    scored = None
    try:
        root = args.base.rstrip("/")
        artifact = root+"/"+args.training_run+"/models/"+args.model_version
        report = json.loads(spark.read.text(artifact+"/report").first()["value"])
        if report.get("feature_set", "baseline") != "baseline":
            raise ValueError("Modèle à historique destinataire : expérimental, non branché au scoring en flux.")
        model = PipelineModel.load(artifact+"/"+report["selected"])
        # Les cibles et les quatre soldes sont absents avant même l'inférence.
        data = (spark.read.parquet(root+"/"+args.run_id+"/curated")
                .select("transaction_id", "source_row", "source", "target", "type", "amount", "step", "event_time")
                .dropDuplicates(["transaction_id"]))
        reference = (spark.read.parquet(root+"/"+args.training_run+"/curated")
                     .filter(F.col("step") <= report["split"]["train_end_step"])
                     .groupBy("type").agg(F.expr("percentile_approx(amount, 0.95, 10000)").alias("training_amount_p95")))
        global_version = args.training_run+":"+args.model_version
        transformed = model.transform(data)
        explanation_columns = []
        if report["selected"] == "logistic_regression":
            classifier = model.stages[-1]
            coefficients = [float(value) for value in classifier.coefficients]
            # StandardScaler conserve l'ordre mais pas les noms d'attributs du VectorAssembler.
            attributes = transformed.schema["unscaled_features"].metadata["ml_attr"]["attrs"]
            names = {item["idx"]: item["name"] for group in attributes.values() for item in group}
            values = vector_array_column("features")
            contributions = [values[index]*F.lit(coefficient) for index, coefficient in enumerate(coefficients)]
            margin = F.lit(float(classifier.intercept))
            for contribution in contributions:
                margin = margin+contribution
            transformed = (transformed.withColumn("linear_intercept", F.lit(float(classifier.intercept)))
                .withColumn("linear_logit", margin)
                .withColumn("linear_contributions", F.array(*[
                    F.struct(F.lit(names[index]).alias("feature"), values[index].alias("standardized_value"),
                             F.lit(coefficients[index]).alias("coefficient"), contribution.alias("logit_contribution"))
                    for index, contribution in enumerate(contributions)])))
            # Vérification sur les vrais vecteurs du modèle rechargé, avant toute publication.
            if transformed.filter(F.abs(F.col("linear_logit")-score_column("rawPrediction")) > 1e-8).limit(1).count():
                raise AssertionError("Décomposition locale différente de la marge du modèle")
            explanation_columns = ["linear_intercept", "linear_logit", "linear_contributions"]
        scored = (transformed.withColumn("score", score_column()).join(reference, "type", "left")
                  .withColumn("threshold", F.lit(report["threshold"]))
                  .withColumn("is_alert", F.col("score") >= F.col("threshold"))
                  .withColumn("amount_above_training_p95", F.col("amount") > F.col("training_amount_p95"))
                  .withColumn("model_version", F.lit(global_version)).withColumn("model_name", F.lit(report["selected"]))
                  .withColumn("run_id", F.lit(args.run_id)).withColumn("scored_at", F.current_timestamp())
                  .withColumn("score_kind", F.lit("uncalibrated_model_score"))
                  .withColumn("_id", F.sha2(F.concat_ws("|", "model_version", "transaction_id"), 256))
                  .select("_id", "transaction_id", "source_row", "source", "target", "type", "amount", "step", "event_time",
                          "score", "threshold", "is_alert", "model_version", "model_name", "run_id", "scored_at", "score_kind",
                          "training_amount_p95", "amount_above_training_p95", *explanation_columns).cache())
        counts = scored.agg(F.count("*").alias("transactions"), F.sum(F.col("is_alert").cast("long")).alias("alerts")).first().asDict()
        if counts["transactions"] == 0:
            raise ValueError("Aucune transaction à scorer.")
        uri = mongo_spark_uri(os.environ["MONGO_APP_PASSWORD"])
        (scored.write.format("mongodb").mode("append").option("connection.uri", uri).option("database", "fraud")
         .option("collection", "fraud_scores").option("operationType", "replace").option("idFieldList", "_id")
         .option("upsertDocument", "true").save())
        print(json.dumps({"event": "fraud_scores_published", "model_version": global_version, "run_id": args.run_id,
                          "linear_decomposition_verified": bool(explanation_columns),
                          **counts, "scope": "Démonstration de scoring ; seule la partition test du rapport mesure la performance."}))
    finally:
        if scored is not None:
            scored.unpersist()
        spark.stop()


if __name__ == "__main__":
    main()
