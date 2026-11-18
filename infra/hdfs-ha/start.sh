#!/usr/bin/env bash
set -euo pipefail
export HADOOP_CONF_DIR=/tmp/ha-conf
python3 /scripts/configure.py
mkdir -p "${HADOOP_LOG_DIR:?}"
role="${1:?Rôle requis}"
case "$role" in
  journalnode) exec hdfs journalnode ;;
  datanode) exec hdfs datanode ;;
  zk-init)
    if [[ ! -f /state/zk.done ]]; then
      hdfs zkfc -formatZK -nonInteractive
      touch /state/zk.done
    fi ;;
  namenode)
    if [[ ! -f /data/name/current/VERSION ]]; then
      [[ -z "$(ls -A /data/name)" ]] || { echo 'Nonempty namespace: refusing initialization' >&2; exit 1; }
      if [[ "$NODE_ID" == nn1 ]]; then
        runuser -u hadoop -- hdfs namenode -format -nonInteractive -clusterid CID-bc1-ha
      else
        ready=false
        for attempt in $(seq 1 60); do
          if [[ "$(hdfs haadmin -getServiceState nn1 2>/dev/null)" == active ]]; then ready=true; break; fi
          sleep 1
        done
        "$ready" || { echo 'nn1 did not become active' >&2; exit 1; }
        runuser -u hadoop -- hdfs namenode -bootstrapStandby -nonInteractive
      fi
    fi
    mkdir -p /run/sshd
    /usr/sbin/sshd -D -e -f /scripts/sshd_config &
    ssh_pid=$!
    runuser -u hadoop -- hdfs namenode &
    nn_pid=$!
    trap 'kill "$nn_pid" "$ssh_pid" 2>/dev/null || true; wait || true' TERM INT
    ready=false
    for attempt in $(seq 1 60); do
      if hdfs haadmin -getServiceState "$NODE_ID" >/dev/null 2>&1; then ready=true; break; fi
      sleep 1
    done
    "$ready" || { echo 'Local NameNode did not start' >&2; exit 1; }
    runuser -u hadoop -- env HADOOP_HEAPSIZE_MAX=128 hdfs zkfc &
    wait "$ssh_pid" ;;
  probe)
    exec java -Xmx384m -cp "/opt/bc1-ha/classes:$(hdfs classpath)" HaContinuityProbe "${2:?Run id}" ;;
  status)
    hdfs haadmin -getAllServiceState ;;
  *) exec "$@" ;;
esac
