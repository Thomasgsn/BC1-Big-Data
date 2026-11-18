#!/usr/bin/env bash
set -euo pipefail
# À exécuter dans postgres avec l'identité locale propriétaire ; jamais dans la base cible existante.
backup="/tmp/bc1-restore-$(date +%s)"
target="bc1_restore_test_$(date +%s)"
pg_dump -U bc1owner -d bc1 -Fc -f "$backup.dump"
createdb -U bc1owner "$target"
pg_restore -U bc1owner -d "$target" --no-owner --exit-on-error "$backup.dump"
query="SELECT (SELECT count(*) FROM investigation_case)::text || chr(44) || (SELECT count(*) FROM analyst_decision)::text || chr(44) || (SELECT count(*) FROM api_principal)::text"
source_counts="$(psql -U bc1owner -d bc1 -Atc "$query")"
restored_counts="$(psql -U bc1owner -d "$target" -Atc "$query")"
test "$source_counts" = "$restored_counts"
sha256sum "$backup.dump"
echo "SQL_RESTORE_PASS database=$target counts=$restored_counts isolated=true"
