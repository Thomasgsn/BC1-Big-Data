"""Secrets de déploiement en volumes privés ; aucune migration des volumes existants."""
import os
from pathlib import Path
import secrets
import subprocess

os.umask(0o077)
def cmd(*args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=90)
    if r.returncode:raise RuntimeError('Provision failed: '+args[0])

ca=Path('/ca');ca.mkdir(exist_ok=True)
if not (ca/'root.crt').exists():
    if list(ca.iterdir()):raise RuntimeError('Partial CA; refusing replacement')
    cmd('openssl','req','-x509','-newkey','rsa:3072','-nodes','-days','365','-subj','/CN=BC1 certification data services CA','-keyout',str(ca/'root.key'),'-out',str(ca/'root.crt'))
public=Path('/public-ca');public.mkdir(exist_ok=True);public.chmod(0o755)
(public/'ca.crt').write_bytes((ca/'root.crt').read_bytes());(public/'ca.crt').chmod(0o444)
if not (public/'trust.jks').exists():
    cmd('keytool','-importcert','-noprompt','-alias','bc1-certification-ca','-file',str(public/'ca.crt'),'-keystore',str(public/'trust.jks'),'-storetype','JKS','-storepass','changeit')
(public/'trust.jks').chmod(0o444) # Truststore de CA publique, pas une identité privée.
for role,uid in [('postgres',999),('mongo',999),('api',10001)]:
    p=Path('/identities')/role;p.mkdir(exist_ok=True)
    if not (p/'complete').exists():
        if list(p.iterdir()):raise RuntimeError('Partial identity '+role)
        cmd('openssl','req','-new','-newkey','rsa:3072','-nodes','-subj','/CN='+role,'-keyout',str(p/'key.pem'),'-out',str(p/'request.csr'))
        ext=p/'extensions';ext.write_text('subjectAltName=DNS:'+role+(',DNS:localhost,IP:127.0.0.1' if role=='api' else '')+'\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n')
        cmd('openssl','x509','-req','-in',str(p/'request.csr'),'-CA',str(ca/'root.crt'),'-CAkey',str(ca/'root.key'),'-CAcreateserial','-days','90','-extfile',str(ext),'-out',str(p/'cert.pem'))
        (p/'server.pem').write_bytes((p/'key.pem').read_bytes()+(p/'cert.pem').read_bytes())
        (p/'complete').touch()
    for f in p.iterdir():os.chown(f,uid,uid);f.chmod(0o400)
    os.chown(p,uid,uid);p.chmod(0o500)
spark=Path('/spark-auth');spark.mkdir(exist_ok=True)
if not (spark/'spark-defaults.conf').exists():
    (spark/'spark-defaults.conf').write_text('spark.authenticate true\nspark.authenticate.secret '+secrets.token_hex(32)+'\nspark.network.crypto.enabled true\nspark.network.crypto.saslFallback false\nspark.io.encryption.enabled true\nspark.ui.enabled false\nspark.master.rest.enabled false\nspark.sql.shuffle.partitions 2\nspark.driver.extraJavaOptions -Djavax.net.ssl.trustStore=/public-ca/trust.jks -Djavax.net.ssl.trustStorePassword=changeit\nspark.executor.extraJavaOptions -Djavax.net.ssl.trustStore=/public-ca/trust.jks -Djavax.net.ssl.trustStorePassword=changeit\n')
config = spark/'spark-defaults.conf'
content = config.read_text()
for key,value in {'spark.hadoop.mapreduce.job.credentials.binary':'/tmp/hadoop.tokens','spark.hadoop.mapreduce.job.hdfs-servers.token-renewal.exclude':'namenode.bc1.test'}.items():
    if not any(line.startswith(key+' ') for line in content.splitlines()):
        content += key+' '+value+'\n'
config.write_text(content)
for f in spark.iterdir():os.chown(f,1000,1000);f.chmod(0o400)
os.chown(spark,1000,1000);spark.chmod(0o500)
for role,uid in [('postgres',999),('mongo',999)]:
    p=Path('/storage')/role;p.mkdir(exist_ok=True);os.chown(p,uid,uid);p.chmod(0o700)
print('{"event":"certification_identities_ready","private_keys":"runtime volumes only"}')
