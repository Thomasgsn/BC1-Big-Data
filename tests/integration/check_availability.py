"""Vérifier un code HTTP attendu pendant un essai de panne orchestré extérieurement."""

import argparse
import json
import os
import time
import urllib.request
import urllib.error

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--expected-status", type=int, required=True)
args = parser.parse_args()
request = urllib.request.Request("http://api:8000/v1/alerts?limit=1",
                                headers={"Authorization": "Bearer "+os.environ["API_TOKEN_ANALYST"]})
begin = time.monotonic()
try:
    with urllib.request.urlopen(request, timeout=12) as response:
        status, body = response.status, json.load(response)
except urllib.error.HTTPError as error:
    status, body = error.code, json.load(error)
if status != args.expected_status:
    raise AssertionError(f"Statut inattendu {status}, attendu {args.expected_status}")
if status == 503 and set(body) != {"detail"}:
    raise AssertionError("Erreur API non bornée")
print(json.dumps({"event": "dependency_availability_verified", "expected_status": args.expected_status,
                  "observed_status": status, "elapsed_seconds": time.monotonic()-begin}))
