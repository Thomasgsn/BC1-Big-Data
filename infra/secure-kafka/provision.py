"""Identités de laboratoire en volumes privés ; aucune clé dans le dépôt."""
import os
from pathlib import Path
import secrets
import subprocess

os.umask(0o077)

def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ca = Path('/ca'); ca.mkdir(exist_ok=True)
if not (ca/'ca.crt').exists():
    run('openssl','req','-x509','-newkey','rsa:3072','-nodes','-days','365','-subj','/CN=BC1 Kafka lab CA','-keyout',str(ca/'ca.key'),'-out',str(ca/'ca.crt'))
for role in ('broker','admin','producer','consumer','intruder'):
    p=Path('/identities')/role;p.mkdir(exist_ok=True)
    if not (p/'complete').exists():
        # Une génération inachevée est refusée plutôt que remplacée silencieusement.
        if list(p.iterdir()): raise RuntimeError('Partial identity: '+role)
        pw=secrets.token_hex(32);(p/'password').write_text(pw)
        run('openssl','req','-new','-newkey','rsa:3072','-nodes','-subj','/CN='+role,'-keyout',str(p/'key.pem'),'-out',str(p/'request.csr'))
        ext=p/'extensions';ext.write_text('subjectAltName=DNS:broker\nextendedKeyUsage=serverAuth,clientAuth\n' if role=='broker' else 'extendedKeyUsage=clientAuth\n')
        run('openssl','x509','-req','-in',str(p/'request.csr'),'-CA',str(ca/'ca.crt'),'-CAkey',str(ca/'ca.key'),'-CAcreateserial','-days','90','-extfile',str(ext),'-out',str(p/'cert.pem'))
        run('openssl','pkcs12','-export','-in',str(p/'cert.pem'),'-inkey',str(p/'key.pem'),'-certfile',str(ca/'ca.crt'),'-out',str(p/'identity.p12'),'-passout','file:'+str(p/'password'))
        run('keytool','-importcert','-noprompt','-alias','bc1-ca','-file',str(ca/'ca.crt'),'-keystore',str(p/'trust.p12'),'-storetype','PKCS12','-storepass:file',str(p/'password'))
        (p/'ca.crt').write_bytes((ca/'ca.crt').read_bytes())
        config='security.protocol=SSL\nssl.keystore.type=PKCS12\nssl.keystore.location=/identity/identity.p12\nssl.keystore.password='+pw+'\nssl.key.password='+pw+'\nssl.truststore.type=PKCS12\nssl.truststore.location=/identity/trust.p12\nssl.truststore.password='+pw+'\nssl.endpoint.identification.algorithm=https\n'
        (p/'client.properties').write_text(config)
        if role=='broker':
            config='broker.id=1\nzookeeper.connect=zk:2181\nlisteners=SSL://0.0.0.0:9093\nadvertised.listeners=SSL://broker:9093\ninter.broker.listener.name=SSL\nlog.dirs=/data/logs\nnum.partitions=1\noffsets.topic.replication.factor=1\ntransaction.state.log.replication.factor=1\ntransaction.state.log.min.isr=1\nauto.create.topics.enable=false\nssl.client.auth=required\nauthorizer.class.name=kafka.security.authorizer.AclAuthorizer\nallow.everyone.if.no.acl.found=false\nsuper.users=User:CN=admin;User:CN=broker\n'+ '\n'.join(x for x in config.splitlines() if x.startswith('ssl.'))+'\n'
            (p/'server.properties').write_text(config)
        (p/'complete').touch()
    for f in p.iterdir(): os.chown(f,1000,1000);f.chmod(0o400)
    os.chown(p,1000,1000);p.chmod(0o500)
for name in ('broker','zk'):
    p=Path('/storage')/name;p.mkdir(exist_ok=True);os.chown(p,1000,1000);p.chmod(0o700)
print('{"event":"kafka_private_identities_ready","roles":5,"runtime_volume_only":true}')
