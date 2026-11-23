"""Contrôler l'inscription du worker auprès du master, sans modifier le cluster."""

import argparse
import json
import socket
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-host", default=socket.gethostname())
    parser.add_argument("--master-url", default="http://spark-master:8080/json/")
    args = parser.parse_args()
    with urllib.request.urlopen(args.master_url, timeout=3) as response:
        payload = response.read(1024*1024+1)
    if len(payload) > 1024*1024:
        raise RuntimeError("Réponse du master dépassant la borne du contrôle")
    workers = json.loads(payload).get("workers", [])
    alive = any(worker.get("state") == "ALIVE" and worker.get("host") == args.expected_host
                and worker.get("cores", 0) > 0 for worker in workers)
    print(json.dumps({"event": "spark_worker_registration", "host": args.expected_host,
                      "registered_alive": alive}))
    return 0 if alive else 1


if __name__ == "__main__":
    raise SystemExit(main())
