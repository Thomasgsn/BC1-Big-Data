#!/usr/bin/env bash
# Plateforme BC1 sécurisée, indépendante du laboratoire historique.
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose --env-file .env -f infra/certification/compose.yml)
action="${1:-status}"; shift || true
case "$action" in
  config) "${compose[@]}" config --quiet ;;
  up) "${compose[@]}" up -d --wait --wait-timeout 300
      "${compose[@]}" run --rm --no-deps kafka-admin ;;
  status) "${compose[@]}" ps ;;
  connectors) "${compose[@]}" run --rm --no-deps fetch-connectors ;;
  driver|producer) "${compose[@]}" run --rm --no-deps "$action" "$@" ;;
  tests) "${compose[@]}" run --rm --no-deps security-tests
         "${compose[@]}" run --rm --no-deps api-tests
         "${compose[@]}" run --rm --no-deps browser-tests ;;
  genai) "${compose[@]}" --profile genai up -d --no-deps ollama ;;
  ca) mkdir -p exports; "${compose[@]}" cp api:/public-ca/ca.crt exports/certification-ca.crt ;;
  *) echo 'Usage : certification.sh {config|up|status|connectors|driver|producer|tests|genai|ca}' >&2; exit 2 ;;
esac
