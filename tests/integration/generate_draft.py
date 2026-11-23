"""Déclencher un vrai brouillon sur une alerte persistée ; ne transmet aucun email."""

import json
import argparse
import os
import ssl
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transaction-id")
    args = parser.parse_args()
    base = os.environ.get("BC1_API_BASE_URL", "http://api:8000")
    tls = ssl.create_default_context(cafile=os.environ["BC1_API_TLS_CA"]) if os.environ.get("BC1_API_TLS_CA") else None
    token = os.environ["API_TOKEN_ANALYST"]
    headers = {"Authorization": "Bearer "+token}
    with urllib.request.urlopen(urllib.request.Request(base+"/v1/alerts?limit=1", headers=headers), timeout=10, context=tls) as response:
        alerts = json.load(response)["items"]
    if not alerts:
        raise RuntimeError("Aucune alerte modèle réelle disponible ; aucune substitution artificielle.")
    identifier = args.transaction_id or alerts[0]["transaction_id"]
    request = urllib.request.Request(base+"/v1/alerts/"+identifier+"/explanations", method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=200, context=tls) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        print(json.dumps({"event": "llm_draft_failed", "status": error.code, "detail": json.load(error)}))
        return 1
    print(json.dumps({"event": "llm_draft_generated", "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
