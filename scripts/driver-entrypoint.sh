#!/usr/bin/env bash
set -euo pipefail
# Chaque driver annonce son adresse propre, même si plusieurs jobs sont en attente.
address="$(python3 -c 'import socket; print(socket.gethostbyname(socket.gethostname()))')"
export SPARK_LOCAL_IP="$address"
cores="${SPARK_CORES_MAX:-2}"
[[ "$cores" =~ ^[1-8]$ ]] || { echo 'SPARK_CORES_MAX doit être compris entre 1 et 8' >&2; exit 2; }
flags=(--master spark://spark-master:7077 --driver-memory 768m --executor-memory 1g
  --conf "spark.cores.max=$cores" --conf spark.executor.cores=2 --conf "spark.driver.host=$address"
  --conf spark.driver.bindAddress=0.0.0.0 --conf spark.jars.ivy=/tmp/ivy)
packages="${SPARK_DRIVER_PACKAGES-org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8}"
if [[ -n "$packages" ]]; then flags+=(--packages "$packages"); fi
exec /opt/spark/bin/spark-submit "${flags[@]}" "$@"
