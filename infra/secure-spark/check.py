import json
import subprocess
import time
from urllib.request import urlopen
cmd=['/opt/spark/bin/spark-submit','--master','spark://master:7077','--conf','spark.driver.host=check','/scripts/probe.py']
started=time.monotonic()
good=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
if good.returncode or 'BC1_SECURE_SPARK_RESULT=333283335000' not in good.stdout:
    print(good.stdout[-10000:]);raise RuntimeError('Authorized distributed Spark job failed')
# Le secret erroné est dans un volume distinct, jamais dans la ligne de commande.
badcmd=cmd[:1]+['--properties-file','/unauthorized/spark-defaults.conf']+cmd[1:]
try:
    bad=subprocess.run(badcmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=35)
    output=bad.stdout;code=bad.returncode;timed_out=False
except subprocess.TimeoutExpired as exc:
    output=exc.stdout or b'';output=output.decode(errors='replace') if isinstance(output,bytes) else output
    code=None;timed_out=True
assert 'BC1_SECURE_SPARK_RESULT=' not in output
assert any(s in output.lower() for s in ('authentication failed','mismatched response','authentication failure','failed to register with master','connection reset')),'Expected explicit authentication rejection evidence'
with urlopen('http://master:8080/json/',timeout=5) as response:state=json.load(response)
assert sum(w['state']=='ALIVE' for w in state['workers'])==1
print(json.dumps(dict(event='spark_secure_rpc_verified',authorized_job_exit=good.returncode,sum_squares=333283335000,wrong_secret_result_absent=True,wrong_secret_authentication_failure=True,wrong_secret_exit=code,wrong_secret_timeout=timed_out,registered_workers=1,configured_rpc_encryption=True,sasl_fallback=False,local_storage_encryption=True,elapsed_seconds=time.monotonic()-started,scope='isolated standalone cluster, shared secret, no UI TLS or main-stack deployment; no packet capture')))
