#!/usr/bin/env bash
set -euo pipefail
case "${1:?namenode ou datanode requis}" in
  namenode)
    if [[ ! -f /data/name/current/VERSION ]]; then
      # Initialisation uniquement sur volume neuf ; ne jamais reformater un volume existant.
      if [[ -n "$(ls -A /data/name)" ]]; then
        echo 'Volume NameNode non vide sans VERSION : arrêt pour préserver les données.' >&2
        exit 1
      fi
      hdfs namenode -format -nonInteractive bc1-local
    fi
    exec hdfs namenode
    ;;
  datanode) exec hdfs datanode ;;
  *) echo 'Service HDFS inconnu.' >&2; exit 2 ;;
esac
