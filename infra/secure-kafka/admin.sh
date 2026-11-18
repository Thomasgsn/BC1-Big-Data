#!/usr/bin/env bash
set -euo pipefail
cli=(--bootstrap-server broker:9093 --command-config /identity/client.properties)
/opt/kafka/bin/kafka-topics.sh "${cli[@]}" --create --if-not-exists --topic secure.transactions --partitions 1 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh "${cli[@]}" --create --if-not-exists --topic forbidden --partitions 1 --replication-factor 1
/opt/kafka/bin/kafka-acls.sh "${cli[@]}" --add --allow-principal User:CN=producer --producer --topic secure.transactions
/opt/kafka/bin/kafka-acls.sh "${cli[@]}" --add --allow-principal User:CN=consumer --consumer --topic secure.transactions --group secure-reader
