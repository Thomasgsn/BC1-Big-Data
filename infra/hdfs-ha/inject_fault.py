"""Panne de processus ciblée dans le seul profil HA, après handshake du probe."""

import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

run_id = sys.argv[1]
if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}",run_id):
    raise ValueError("Run id invalide")
node = socket.gethostname()
if node not in {"nn1","nn2"}:
    raise RuntimeError("Exécution hors du profil cible refusée")
control = Path("/control")/run_id
if not (control/"ready.json").exists():
    raise RuntimeError("Émetteur non prêt")
state = subprocess.run(["hdfs","haadmin","-getServiceState",node],capture_output=True,text=True,check=True).stdout.strip()
if state != "active":
    raise RuntimeError("Le nœud ciblé n'est pas actif")
pids=[]
for directory in Path('/proc').iterdir():
    if not directory.name.isdigit():continue
    try:args=(directory/'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,PermissionError,ProcessLookupError):continue
    if b'org.apache.hadoop.hdfs.server.namenode.NameNode' in args:pids.append(int(directory.name))
if len(pids)!=1 or pids[0]<=1:raise RuntimeError('Un unique processus NameNode est requis')
(control/'inject-now').touch(exist_ok=False)
time.sleep(0.2)
report={'event':'namenode_process_killed','node':node,'pid':pids[0],'signal':'SIGKILL','at_epoch_ms':time.time_ns()//1000000}
os.kill(pids[0],signal.SIGKILL)
(control/'fault.json').write_text(json.dumps(report)+'\n')
print(json.dumps(report))
