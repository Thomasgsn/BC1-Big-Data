import os
from pathlib import Path
import secrets
os.umask(0o077)
for role in ('authorized','unauthorized'):
    p=Path('/identities')/role;p.mkdir(exist_ok=True)
    f=p/'spark-defaults.conf'
    if not f.exists():
        f.write_text('spark.authenticate true\nspark.authenticate.secret '+secrets.token_hex(32)+'\nspark.network.crypto.enabled true\nspark.network.crypto.saslFallback false\nspark.io.encryption.enabled true\nspark.ui.enabled false\nspark.driver.memory 512m\nspark.executor.memory 512m\nspark.cores.max 1\nspark.executor.cores 1\n')
    os.chown(f,185,185);f.chmod(0o400);os.chown(p,185,185);p.chmod(0o500)
print('{"event":"spark_private_configs_ready","secret_values_logged":false}')
