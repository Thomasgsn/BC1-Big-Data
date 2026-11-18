#!/usr/bin/env bash
# Copie de validation uniquement : aucune suppression ni écriture dans la source.
set -euo pipefail
for target in /target-name /target-data; do
  if [[ -n "$(ls -A "$target")" ]]; then
    echo 'Destination non vide : copie refusée pour préserver ses données.' >&2
    exit 1
  fi
done
test -f /source-name/current/VERSION
test -f /source-data/current/VERSION
fingerprint() {
  (cd "$1" && find . -type f -exec sha256sum {} + | LC_ALL=C sort) | sha256sum | cut -d' ' -f1
}
name_before="$(fingerprint /source-name)"
data_before="$(fingerprint /source-data)"
cp -a /source-name/. /target-name/
cp -a /source-data/. /target-data/
test "$name_before" = "$(fingerprint /target-name)"
test "$data_before" = "$(fingerprint /target-data)"
test "$name_before" = "$(fingerprint /source-name)"
test "$data_before" = "$(fingerprint /source-data)"
printf '{"event":"hdfs_volumes_cloned","file_hash_sets_match":true,"source_hashes_unchanged":true,"namenode_tree_sha256":"%s","datanode_tree_sha256":"%s","source_mounts":"declared read-only in Compose","scope":"source NN/DN must be stopped by caller before copy"}\n' "$name_before" "$data_before"
