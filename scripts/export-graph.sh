#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
snapshot="${1:?Snapshot requis : run-id-steps-from-to}"
[[ "$snapshot" =~ ^[a-zA-Z0-9_-]{1,150}$ ]] || { echo 'Snapshot invalide' >&2; exit 2; }
mkdir -p exports/mongo
input="exports/mongo/$snapshot.json"
# Mongo refuse l'écrasement ; aucun mot de passe dans les arguments ou la sortie.
docker compose exec -T -e BC1_SNAPSHOT_ID="$snapshot" -e BC1_EXPORT_FILE="/exports/mongo/$snapshot.json" \
  mongo mongosh --nodb --quiet --file /opt/bc1/export.js
PYTHONPATH=src .venv/bin/python -m rncp_bc1.graph_export --input "$input" --destination "exports/gephi/$snapshot"
