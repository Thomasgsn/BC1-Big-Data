"""Déclencher un vrai brouillon sur une alerte persistée ; ne transmet aucun email."""

import json
import argparse
import os
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transaction-id")
    args = parser.parse_args()
    token = os.environ["API_TOKEN_ANALYST"]
    headers = {"Authorization": "Bearer "+token}
    with urllib.request.urlopen(urllib.request.Request("http://api:8000/v1/alerts?limit=1", headers=headers), timeout=10) as response:
        alerts = json.load(response)["items"]
    if not alerts:
        raise RuntimeError("Aucune alerte modèle réelle disponible ; aucune substitution artificielle.")
    identifier = args.transaction_id or alerts[0]["transaction_id"]
    request = urllib.request.Request("http://api:8000/v1/alerts/"+identifier+"/explanations", method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=200) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        print(json.dumps({"event": "llm_draft_failed", "status": error.code, "detail": json.load(error)}))
        return 1
    print(json.dumps({"event": "llm_draft_generated", "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
