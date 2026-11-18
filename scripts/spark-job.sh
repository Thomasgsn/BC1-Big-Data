#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
job="${1:?Usage : spark-job.sh {ingest|verify|publish_graph|train|probe_sql} arguments}"
shift
case "$job" in
  ingest) packages=org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8 ;;
  publish_graph|score) packages=org.mongodb.spark:mongo-spark-connector_2.12:10.7.0 ;;
  probe_sql|extract_reviews) packages=org.postgresql:postgresql:42.7.14 ;;
  verify|train|probe_ml|benchmark_compute|optimize_parquet) packages= ;;
  *) echo 'Job inconnu' >&2; exit 2 ;;
esac
exec docker compose run --rm -e SPARK_DRIVER_PACKAGES="$packages" \
  spark-driver "/project/src/rncp_bc1/jobs/$job.py" "$@"
