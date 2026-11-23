"""Historique des comptes destinataires, calculé sans label ni information future.

PaySim réutilise presque jamais un compte émetteur (99,7 % des lignes uniques) :
l'écart à la moyenne d'un compte est donc calculé sur le compte destinataire.
Chaque fenêtre ne voit que les steps strictement antérieurs : une transaction
du même step (même heure simulée) n'est jamais utilisée.
"""

FEATURE_SETS = ("baseline", "destination_history")
BASELINE_FEATURES = ["log_amount", "hour_sin", "hour_cos", "type_vector"]
DESTINATION_FEATURES = ["dest_prior_count_log", "dest_prior_24h_log", "amount_vs_dest_mean", "dest_first_seen"]


def features_for(feature_set):
    if feature_set == "baseline":
        return list(BASELINE_FEATURES)
    if feature_set == "destination_history":
        return BASELINE_FEATURES + DESTINATION_FEATURES
    raise ValueError("Jeu de variables inconnu : baseline ou destination_history.")


def add_destination_history(data):
    """Ajoute quatre variables ; requiert les colonnes target, step et amount."""
    from pyspark.sql import Window, functions as F
    ordered = Window.partitionBy("target").orderBy(F.col("step").cast("long"))
    prior = ordered.rangeBetween(Window.unboundedPreceding, -1)
    last_day = ordered.rangeBetween(-24, -1)
    amount = F.col("amount").cast("double")
    count = F.count(F.lit(1)).over(prior)
    mean = F.avg(amount).over(prior)
    return (data
            .withColumn("dest_prior_count_log", F.log1p(count.cast("double")))
            .withColumn("dest_prior_24h_log", F.log1p(F.count(F.lit(1)).over(last_day).cast("double")))
            .withColumn("amount_vs_dest_mean", F.when(count > 0, F.log1p(amount) - F.log1p(mean)).otherwise(F.lit(0.0)))
            .withColumn("dest_first_seen", F.when(count == 0, F.lit(1.0)).otherwise(F.lit(0.0))))
