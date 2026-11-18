#!/usr/bin/env bash
# Lanceur local BC1 ; aucun nettoyage de volumes ni publication.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then
  bc1_python=.venv/bin/python
elif command -v python3.13 >/dev/null; then
  bc1_python=python3.13
else
  bc1_python=python3
fi
"$bc1_python" scripts/bootstrap.py
docker compose config --quiet
action="${1:-up}"
case "$action" in
  up)
    docker compose up -d --build --wait --wait-timeout 300
    "$bc1_python" -c 'import subprocess; subprocess.run(["docker","compose","exec","-T","namenode","hdfs","dfsadmin","-safemode","wait"],timeout=90,check=True)'
    docker compose exec -T namenode hdfs dfs -mkdir -p /bc1
    docker compose exec -T namenode hdfs dfs -chmod 700 /bc1
    docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 \
      --create --if-not-exists --topic transactions.v1 --partitions 3 --replication-factor 1
    ;;
  smoke)
    bash scripts/stack.sh up
    run_id="smoke-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    limit="${BC1_SMOKE_LIMIT:-1000}"
    [[ "$limit" =~ ^[1-9][0-9]*$ ]] || { echo 'BC1_SMOKE_LIMIT invalide' >&2; exit 2; }
    mkdir -p logs docs/evidence/p2-p3
    export REPLAY_RUN_ID="$run_id" REPLAY_LIMIT="$limit" REPLAY_RATE_PER_SECOND=100
    log_file="logs/$run_id.log"
    report="docs/evidence/p2-p3/$run_id.json"
    trap 'status=$?; printf "{\"run_id\":\"%s\",\"limit\":%s,\"exit_code\":%s,\"actor\":\"terminal\",\"log_file\":\"%s\"}\n" "$run_id" "$limit" "$status" "$log_file" > "$report"' EXIT
    bash scripts/spark-job.sh probe_sql 2>&1 | tee "$log_file"
    docker compose run --rm --no-deps producer 2>&1 | tee -a "$log_file"
    docker compose run --rm spark-driver /project/src/rncp_bc1/jobs/ingest.py \
      --run-id "$run_id" --once 2>&1 | tee -a "$log_file"
    docker compose run --rm -e SPARK_DRIVER_PACKAGES= spark-driver /project/src/rncp_bc1/jobs/verify.py \
      --run-id "$run_id" --limit "$limit" \
      --csv /project/data/raw/PS_20174392719_1491204439457_log.csv 2>&1 | tee -a "$log_file"
    echo "Contrôle initial réussi. Redémarrage des composants de stockage sans suppression de volumes."
    docker compose restart kafka namenode datanode
    docker compose up -d --wait --wait-timeout 300
    docker compose run --rm -e SPARK_DRIVER_PACKAGES= spark-driver /project/src/rncp_bc1/jobs/verify.py \
      --run-id "$run_id" --limit "$limit" \
      --csv /project/data/raw/PS_20174392719_1491204439457_log.csv 2>&1 | tee -a "$log_file"
    echo "Flux borné et persistance vérifiés ; rapport : $report"
    ;;
  status) docker compose ps ;;
  *) echo 'Usage : bash scripts/stack.sh {up|smoke|status}' >&2; exit 2 ;;
esac
