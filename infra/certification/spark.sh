#!/usr/bin/env bash
set -euo pipefail
unset HADOOP_USER_NAME
export KRB5CCNAME=FILE:/tmp/krb5cc_bc1
kinit -kt /etc/bc1/service.keytab alice@BC1.TEST
env -u HADOOP_TOKEN_FILE_LOCATION java -cp "/etc/bc1:/opt/bc1-security/classes:/opt/spark/jars/*" CredentialBootstrap
export HADOOP_TOKEN_FILE_LOCATION=/tmp/hadoop.tokens
mkdir -p /tmp/spark-work /tmp/spark-logs
if [[ "${1:-}" == worker ]]; then
  # Standalone : chaque worker a son propre cache de tickets, sans renouvellement YARN prétendu.
  (while sleep 300; do kinit -kt /etc/bc1/service.keytab alice@BC1.TEST && env -u HADOOP_TOKEN_FILE_LOCATION java -cp "/etc/bc1:/opt/bc1-security/classes:/opt/spark/jars/*" CredentialBootstrap || exit 1; done) &
  renew_pid=$!
  trap 'kill "$renew_pid" "${worker_pid:-}" 2>/dev/null || true' EXIT
  shift
  /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker --host "$(hostname)" --cores 2 --memory 1536m spark://master:7077 &
  worker_pid=$!
  trap 'kill "$renew_pid" "$worker_pid" 2>/dev/null || true; wait || true' TERM INT
  wait -n "$worker_pid" "$renew_pid"
else
  python3 /runtime/fetch-connectors.py --lock /runtime/connectors.lock.json --directory /connectors-extra --check-only
  address="$(python3 -c 'import socket; print(socket.gethostbyname(socket.gethostname()))')"
  export SPARK_LOCAL_IP="$address"
  jars="$(find /connectors-extra -maxdepth 1 -name '*.jar' -printf '%p,' | sort)"
  jars="${jars%,}"
  exec /opt/spark/bin/spark-submit --master spark://master:7077 --driver-memory 768m --executor-memory 1g \
    --conf spark.cores.max=2 --conf spark.executor.cores=2 --conf "spark.driver.host=$address" \
    --conf spark.driver.bindAddress=0.0.0.0 --jars "$jars" "$@"
fi
