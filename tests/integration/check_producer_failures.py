"""Sous-processus réels : connexion refusée et SIGINT, préfixe PaySim identifié."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

with tempfile.TemporaryDirectory(prefix='producer-failure-',dir='tmp') as temp:
    root=Path(temp);source=root/'paysim-prefix.csv'
    with Path('data/raw/PS_20174392719_1491204439457_log.csv').open('rb') as f:
        source.write_bytes(b''.join(next(f) for _ in range(101)))
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    base=[sys.executable,'-m','rncp_bc1.producer','--csv',str(source),'--sha256',sha,'--run-id','failure-contract-v1','--limit','100']
    started=time.monotonic()
    bad=subprocess.run(base+['--bootstrap-servers','127.0.0.1:1'],capture_output=True,text=True,timeout=45)
    assert bad.returncode==1,bad.stderr
    error=json.loads(bad.stderr.splitlines()[-1]);assert error['event']=='replay_failed' and error['acknowledged_rows']==0
    target=root/'never-partial.jsonl'
    process=subprocess.Popen(base+['--jsonl',str(target),'--rate','2'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+10
    while len(list(root.iterdir()))<2:
        assert process.poll() is None,'Producer exited before interruption'
        if time.monotonic()>deadline:process.kill();raise TimeoutError('Output initialization')
        time.sleep(.02)
    time.sleep(.6);process.send_signal(signal.SIGINT);out,err=process.communicate(timeout=10)
    assert process.returncode==130,err
    interrupted=json.loads(err.splitlines()[-1]);assert interrupted['event']=='replay_failed' and interrupted['error_type']=='KeyboardInterrupt'
    assert interrupted['acknowledged_rows']>=1 and not target.exists()
    assert list(root.iterdir())==[source],'Temporary publication file should be removed'
    print(json.dumps(dict(event='producer_failures_verified',input='first 100 actual PaySim rows, temporary CSV',prefix_sha256=sha,unreachable_broker={'exit_code':bad.returncode,'acknowledged':0,'error_type':error['error_type']},sigint={'exit_code':130,'acknowledged_rows':interrupted['acknowledged_rows'],'partial_output_published':False,'temporary_file_removed':True},elapsed_seconds=time.monotonic()-started)))
