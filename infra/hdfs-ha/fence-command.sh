#!/usr/bin/env bash
# Clé dédiée : seules les deux commandes natives de SshFenceByTcpPort sont permises.
set -euo pipefail
case "${SSH_ORIGINAL_COMMAND:-}" in
  'PATH=$PATH:/sbin:/usr/sbin fuser -v -k -n tcp 8020')
    exec /usr/bin/fuser -v -k -n tcp 8020 ;;
  'nc -z nn1 8020')
    exec /usr/bin/nc -z nn1 8020 ;;
  'nc -z nn2 8020')
    exec /usr/bin/nc -z nn2 8020 ;;
  *) echo 'Fencing key: command refused' >&2; exit 126 ;;
esac
