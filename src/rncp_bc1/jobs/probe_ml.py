"""Sonde Spark réelle des vecteurs dense/creux ; effectifs de test artificiels."""

import json


def main():
    from pyspark.sql import SparkSession
    from pyspark.ml.linalg import Vectors
    from rncp_bc1.jobs.columns import score_column
    spark = SparkSession.builder.appName("bc1-ml-runtime-probe").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        frame = spark.createDataFrame([(Vectors.dense([0.7, 0.3]),), (Vectors.sparse(2, {1: 0.8}),)], ["probability"])
        values = sorted(row["score"] for row in frame.select(score_column().alias("score")).collect())
        if values != [0.3, 0.8]:
            raise AssertionError("Extraction de probabilités incorrecte.")
        print(json.dumps({"event": "spark_ml_vectors_verified", "synthetic_fixture": True, "scores": values}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
