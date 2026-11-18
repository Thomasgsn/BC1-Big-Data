#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${HADOOP_LOG_DIR:?}"
case "${1:?Service requis}" in
  namenode)
    if [[ ! -f /data/name/current/VERSION ]]; then
      [[ -z "$(ls -A /data/name)" ]] || { echo 'Volume non vide : formatage refusé.' >&2; exit 1; }
      hdfs namenode -format -nonInteractive bc1-secure-lab
    fi
    exec hdfs namenode ;;
  datanode) exec hdfs datanode ;;
  *) echo 'Service inconnu' >&2; exit 2 ;;
esac
