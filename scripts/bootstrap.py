#!/usr/bin/env python3
"""Créer une configuration locale sans écraser de secret existant."""

import json
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / ".env"
    if target.exists():
        print(".env existe : conservé sans modification.")
        return
    images = json.loads((ROOT/"infra/images.lock.json").read_text())["images"]
    values = {name.upper()+"_IMAGE": item["reference"] for name, item in images.items()}
    values |= {name: secrets.token_urlsafe(32) for name in ["POSTGRES_PASSWORD", "POSTGRES_APP_PASSWORD",
              "MONGO_PASSWORD", "MONGO_APP_PASSWORD", "API_TOKEN_READER", "API_TOKEN_ANALYST"]}
    values |= {"COMPOSE_FILE": "docker-compose.yml:infra/hadoop-modern/migration.yml",
               "DATASET_SHA256": "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b",
               "REPLAY_RUN_ID": "demo-v1", "REPLAY_LIMIT": "10000", "REPLAY_RATE_PER_SECOND": "100",
               "LLM_MODEL": "qwen2.5:3b", "LLM_BASE_URL": "http://ollama:11434"}
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("# Configuration locale générée ; secrets exclus de Git.\n")
        stream.writelines(f"{key}={value}\n" for key, value in values.items())
    print(".env créé avec permissions 0600 ; aucun secret affiché.")


if __name__ == "__main__":
    main()
