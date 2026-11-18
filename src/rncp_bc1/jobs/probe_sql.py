"""Sonde réelle Spark JDBC et jointure des rôles configurés ; aucune décision fictive."""

import json
import os


def main():
    password = os.environ.get("POSTGRES_APP_PASSWORD")
    if not password:
        raise ValueError("POSTGRES_APP_PASSWORD requis, jamais passé en argument.")
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("bc1-jdbc-probe").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        roles = (spark.read.format("jdbc").option("url", "jdbc:postgresql://postgres:5432/bc1")
                 .option("query", "SELECT DISTINCT role FROM api_principal WHERE active")
                 .option("driver", "org.postgresql.Driver").option("user", "bc1app")
                 .option("password", password).load())
        expected_roles = spark.createDataFrame([("reader",), ("analyst",)], ["role"])
        joined = roles.join(expected_roles, "role", "inner").count()
        if joined != 2 or roles.exceptAll(expected_roles).count() != 0:
            raise AssertionError("Rôles configurés différents des deux rôles attendus.")
        print(json.dumps({"event": "spark_jdbc_verified", "joined_roles": joined,
                          "scope": "configuration des identités ; pas ingestion de décisions métier"}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
