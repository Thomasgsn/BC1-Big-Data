#!/usr/bin/env bash
set -euo pipefail
# Snapshot de données borné ; exclut les journaux absolus FileSink et les checkpoints.
suffix="$(date +%s)"
backup="/tmp/bc1-hdfs-backup-$suffix"
target="/bc1/restore-tests/backup-$suffix"
mkdir -p "$backup/runtime-v1"
for zone in raw curated quarantine; do
  mkdir "$backup/runtime-v1/$zone"
  hdfs dfs -get "/bc1/runtime-v1/$zone/*.parquet" "$backup/runtime-v1/$zone/"
done
hdfs dfs -get /bc1/runtime-v1/metrics "$backup/runtime-v1/metrics"
hdfs dfs -mkdir -p "$target"
hdfs dfs -put "$backup/runtime-v1" "$target/"
find "$backup" -type f -name '*.parquet' -exec sha256sum '{}' + > "$backup/checksums.sha256"
echo "HDFS_SNAPSHOT_RESTORED base=hdfs://namenode:8020$target run_id=runtime-v1 local_backup=$backup"
echo "Read verification must run separately; this line alone is not a successful integrity test."
