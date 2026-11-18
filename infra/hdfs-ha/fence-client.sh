#!/usr/bin/env bash
# ShellCommandFencer standard ; SSH réel, hôtes épinglés et commande distante limitée.
set -euo pipefail
case "${target_host:-}" in nn1|nn2) ;; *) exit 1 ;; esac
[[ "${target_port:-}" == 8020 ]] || exit 1
args=(-i /fence/id_rsa -p 2222 -o BatchMode=yes -o ConnectTimeout=5
      -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/fence/known_hosts)
set +e
ssh "${args[@]}" "hadoop@$target_host" 'PATH=$PATH:/sbin:/usr/sbin fuser -v -k -n tcp 8020'
status=$?
set -e
if [[ "$status" == 0 ]]; then exit 0; fi
[[ "$status" == 1 ]] || exit 1  # Une erreur SSH n'est jamais une preuve de fencing.
set +e
ssh "${args[@]}" "hadoop@$target_host" "nc -z $target_host 8020"
status=$?
set -e
[[ "$status" == 1 ]] && exit 0  # Le port n'écoute effectivement plus.
exit 1
