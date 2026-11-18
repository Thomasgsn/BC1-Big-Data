"""Contrôler les frontières réelles du conteneur API sans lire ni afficher de secret."""

import json
import os
from pathlib import Path
import tempfile

assert os.geteuid() != 0, "API exécutée en root"
assert not Path("/project/.env").exists(), "Configuration secrète hôte montée dans l'API"
assert not Path("/project/data/raw").exists(), "Dataset brut inutilement monté dans l'API"
assert not any(name in os.environ for name in ["POSTGRES_PASSWORD", "MONGO_PASSWORD", "API_TOKEN_READER", "API_TOKEN_ANALYST"]), "Identité propriétaire ou jetons clients injectés dans l'API"
try:
    with tempfile.NamedTemporaryFile(dir="/project", prefix="bc1_write_probe_"):
        writable = True
except OSError:
    writable = False
assert not writable, "Système de fichiers API modifiable"
print(json.dumps({"event": "api_isolation_verified", "uid": os.geteuid(), "host_env_absent": True,
                  "raw_dataset_absent": True, "owner_credentials_and_client_tokens_absent": True,
                  "project_write_denied": True}))
