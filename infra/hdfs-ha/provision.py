"""Préparer volumes HA et clés de fencing ; ne remplace aucune clé existante."""

import os
from pathlib import Path
import subprocess

os.umask(0o077)
fence = Path("/fence")
if not (fence/"id_rsa").exists():
    subprocess.run(["ssh-keygen", "-q", "-t", "rsa", "-b", "3072", "-m", "PEM", "-N", "", "-f", str(fence/"id_rsa")], check=True)
public = (fence/"id_rsa.pub").read_text().strip()
known = []
for node in ["nn1", "nn2"]:
    directory = Path("/ssh")/node
    if not (directory/"ssh_host_rsa_key").exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "rsa", "-b", "3072", "-N", "", "-f", str(directory/"ssh_host_rsa_key")], check=True)
    (directory/"authorized_keys").write_text('restrict,command="/bin/bash /scripts/fence-command.sh" '+public+"\n")
    directory.chmod(0o755)
    (directory/"authorized_keys").chmod(0o444)
    (directory/"ssh_host_rsa_key").chmod(0o400)
    known.append("["+node+"]:2222 "+(directory/"ssh_host_rsa_key.pub").read_text().strip())
(fence/"known_hosts").write_text("\n".join(known)+"\n")
for path in fence.iterdir():
    os.chown(path,1000,1000)
    path.chmod(0o400)
os.chown(fence,1000,1000)
fence.chmod(0o500)
for name in ["nn1", "nn2", "jn1", "jn2", "jn3", "dn1", "dn2", "zk1", "zk2", "zk3", "state", "control"]:
    directory = Path("/storage")/name
    directory.mkdir(exist_ok=True)
    os.chown(directory,1000,1000)
    directory.chmod(0o700)
print('HA volumes and fencing keys prepared; no key material emitted')
