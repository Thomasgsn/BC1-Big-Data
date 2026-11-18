"""Pont ciblé vers l'API Scala Spark 3.5 pour lire un vecteur de probabilités.

Le module Python pyspark.ml.functions importe pandas même pour vector_to_array.
Ce pont emploie la même fonction Scala que le wrapper distribué avec Spark 3.5.8,
sans imposer pandas/Arrow au seul calcul d'un score ; compatibilité testée par probe_ml.
"""


def vector_array_column(name):
    from pyspark import SparkContext
    from pyspark.sql import Column, functions as F
    context = SparkContext._active_spark_context
    if context is None or context._jvm is None:
        raise RuntimeError("Un contexte Spark actif est requis.")
    converted = context._jvm.org.apache.spark.ml.functions.vector_to_array(F.col(name)._jc, "float64")
    return Column(converted)


def score_column(name="probability"):
    return vector_array_column(name)[1]
