"""Comparaison chronologique de deux pipelines Spark MLlib ; pas de solde prédictif.

Le jeu destination_history ajoute l'historique antérieur du compte destinataire
(voir account_features) ; le compte lui-même n'est jamais une variable du modèle.
"""

import argparse
from datetime import datetime, timezone
import json
import time

from rncp_bc1.model_metrics import confusion_metrics, select_threshold
from rncp_bc1.jobs.account_features import FEATURE_SETS, add_destination_history, features_for
from rncp_bc1.transactions import ID_PATTERN

# Grille élargie au-delà de 0,9 : le seuil retenu en bord de grille (0,9) ne montrait pas un optimum.
THRESHOLDS = (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99)


def step_quantiles(step_counts, fractions):
    """Plus petit step dont l'effectif cumulé atteint chaque fraction des lignes."""
    ordered = sorted(step_counts)
    total = sum(count for _, count in ordered)
    if total <= 0:
        raise ValueError("Aucune ligne à découper.")
    result = []
    for fraction in fractions:
        target, cumulative = fraction * total, 0
        for step, count in ordered:
            cumulative += count
            if cumulative >= target:
                result.append(step)
                break
    return result


def evaluate(predictions, threshold):
    from pyspark.sql import functions as F
    from rncp_bc1.jobs.columns import score_column
    data = predictions.withColumn("score", score_column())
    positive = F.col("score") >= threshold
    label = F.col("isFraud") == 1
    expressions = [F.sum(F.when(condition, 1).otherwise(0)).alias(name) for name, condition in [
        ("tp", positive & label), ("fp", positive & ~label), ("tn", ~positive & ~label), ("fn", ~positive & label)]]
    counts = data.agg(*expressions).first().asDict()
    return {"threshold": threshold, **confusion_metrics(**{key: int(value or 0) for key, value in counts.items()})}


def aucs(predictions):
    from pyspark.ml.evaluation import BinaryClassificationEvaluator
    if predictions.select("isFraud").distinct().count() != 2:
        return {"auc_roc": None, "auc_pr": None, "warning": "Une seule classe observée ; AUC indéfinie."}
    return {key: BinaryClassificationEvaluator(labelCol="isFraud", rawPredictionCol="probability", metricName=metric).evaluate(predictions)
            for key, metric in [("auc_roc", "areaUnderROC"), ("auc_pr", "areaUnderPR")]}


def build_pipeline(kind, seed, feature_set="baseline"):
    from pyspark.ml import Pipeline
    from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
    from pyspark.ml.feature import SQLTransformer, StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
    feature_sql = SQLTransformer(statement="""SELECT *, LOG1P(CAST(amount AS DOUBLE)) AS log_amount,
      SIN((step - 1) % 24 * 6.283185307179586 / 24) AS hour_sin,
      COS((step - 1) % 24 * 6.283185307179586 / 24) AS hour_cos FROM __THIS__""")
    indexer = StringIndexer(inputCol="type", outputCol="type_index", handleInvalid="keep")
    encoder = OneHotEncoder(inputCol="type_index", outputCol="type_vector", handleInvalid="keep")
    assembler = VectorAssembler(inputCols=features_for(feature_set), outputCol="unscaled_features")
    scaler = StandardScaler(inputCol="unscaled_features", outputCol="features", withStd=True, withMean=False)
    if kind == "logistic_regression":
        classifier = LogisticRegression(featuresCol="features", labelCol="isFraud", weightCol="class_weight", maxIter=50, regParam=0.1)
    elif kind == "random_forest":
        classifier = RandomForestClassifier(featuresCol="features", labelCol="isFraud", weightCol="class_weight",
                                            numTrees=40, maxDepth=6, seed=seed)
    else:
        raise ValueError("Modèle inconnu")
    return Pipeline(stages=[feature_sql, indexer, encoder, assembler, scaler, classifier])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--base", default="hdfs://namenode:8020/bc1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--feature-set", choices=FEATURE_SETS, default="baseline")
    args = parser.parse_args()
    if not all(ID_PATTERN.fullmatch(x) for x in [args.run_id, args.model_version]):
        parser.error("run-id ou version invalide")
    from pyspark.sql import SparkSession, functions as F
    spark = (SparkSession.builder.appName("bc1-ml-training").config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "2").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    frames = []
    try:
        root = args.base.rstrip("/") + "/" + args.run_id
        # La liste positive supprime physiquement les soldes, comptes et drapeau historique avant le ML.
        columns = ["transaction_id", "step", "type", "amount", "isFraud"]
        if args.feature_set == "destination_history":
            columns.append("target")
        data = spark.read.parquet(root+"/curated").select(*columns).dropDuplicates(["transaction_id"])
        if args.feature_set == "destination_history":
            # Calcul sur toute la chronologie avant découpage : chaque ligne ne voit que des steps antérieurs.
            data = add_destination_history(data).drop("target")
        if data.select("step").distinct().count() < 5:
            raise ValueError("Au moins cinq steps distincts requis pour un découpage temporel défendable ; ingérer une période plus longue.")
        # Quantiles exacts par effectifs de step : quelques centaines de lignes rapatriées, pas toutes les valeurs.
        train_end, validation_end = step_quantiles([(int(r["step"]), int(r["count"])) for r in
                                                    data.groupBy("step").count().collect()], [0.6, 0.8])
        train = data.filter(F.col("step") <= train_end).cache()
        validation = data.filter((F.col("step") > train_end) & (F.col("step") <= validation_end)).cache()
        test = data.filter(F.col("step") > validation_end).cache()
        frames.extend([train, validation, test])
        distribution = {}
        for name, frame in [("train", train), ("validation", validation), ("test", test)]:
            counts = {int(x["isFraud"]): x["count"] for x in frame.groupBy("isFraud").count().collect()}
            if set(counts) != {0, 1}:
                raise ValueError(f"Les deux classes doivent être présentes dans {name}. Augmenter la période sans déplacer de lignes entre périodes.")
            distribution[name] = {"negative": counts[0], "positive": counts[1]}
        total = sum(distribution["train"].values())
        train = train.withColumn("class_weight", F.when(F.col("isFraud") == 1, total/(2*distribution["train"]["positive"]))
                                 .otherwise(total/(2*distribution["train"]["negative"])))
        candidates = []
        fitted = {}
        for name in ["logistic_regression", "random_forest"]:
            started = time.monotonic()
            model = build_pipeline(name, args.seed, args.feature_set).fit(train)
            fit_seconds = time.monotonic()-started
            predictions = model.transform(validation).cache()
            try:
                thresholds = [evaluate(predictions, value) for value in THRESHOLDS]
                chosen = select_threshold(thresholds)
                candidates.append({"name": name, "fit_seconds": fit_seconds, "validation": {**chosen, **aucs(predictions)},
                                   "threshold_candidates": thresholds})
                fitted[name] = model
            finally:
                predictions.unpersist()
        # Sélection sans consultation du test ; départage par PR-AUC, puis F2 validation.
        selected = max(candidates, key=lambda c: (c["validation"]["auc_pr"], c["validation"]["f2"]))
        tests = {}
        for candidate in candidates:
            predictions = fitted[candidate["name"]].transform(test).cache()
            try:
                tests[candidate["name"]] = {**evaluate(predictions, candidate["validation"]["threshold"]), **aucs(predictions)}
            finally:
                predictions.unpersist()
        artifact = root+"/models/"+args.model_version
        for name, model in fitted.items():
            # Pas d'overwrite : une version déjà publiée reste immuable.
            model.write().save(artifact+"/"+name)
        report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": args.run_id,
                  "model_version": args.model_version, "seed": args.seed,
                  "split": {"train_end_step": train_end, "validation_end_step": validation_end, "classes": distribution},
                  "feature_set": args.feature_set, "features": features_for(args.feature_set),
                  "excluded": ["oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "isFlaggedFraud", "account_ids"],
                  "baseline_always_negative": confusion_metrics(0, 0, distribution["test"]["negative"], distribution["test"]["positive"]),
                  "candidates": candidates, "test": tests, "selected": selected["name"],
                  "threshold": selected["validation"]["threshold"], "artifact_path": artifact}
        spark.createDataFrame([(json.dumps(report),)], ["value"]).coalesce(1).write.mode("error").text(artifact+"/report")
        print(json.dumps({"event": "models_evaluated", "report": report}))
    finally:
        for frame in frames:
            frame.unpersist()
        spark.stop()


if __name__ == "__main__":
    main()
