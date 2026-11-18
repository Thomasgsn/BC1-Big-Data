#!/usr/bin/env bash
set -euo pipefail
mkdir -p /data
if [[ ! -f /data/myid ]]; then printf '%s\n' "${ZK_ID:?}" > /data/myid; fi
cat > /tmp/zookeeper.properties <<'EOF'
tickTime=2000
initLimit=10
syncLimit=5
dataDir=/data
clientPort=2181
admin.enableServer=false
server.1=zk1:2888:3888
server.2=zk2:2888:3888
server.3=zk3:2888:3888
4lw.commands.whitelist=ruok,stat
autopurge.snapRetainCount=3
autopurge.purgeInterval=1
EOF
exec /opt/kafka/bin/zookeeper-server-start.sh /tmp/zookeeper.properties
