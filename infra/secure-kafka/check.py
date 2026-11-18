"""Essai réel mTLS/ACL sur un préfixe PaySim, sans volume du principal."""
import hashlib
import json
from pathlib import Path
import socket
import ssl
import time
from kafka import KafkaConsumer,KafkaProducer,TopicPartition
from kafka.errors import TopicAuthorizationFailedError


def tls(role,cert=True,trust=True):
    c=ssl.create_default_context(cafile='/identities/'+role+'/ca.crt') if trust else ssl.create_default_context()
    if cert: c.load_cert_chain('/identities/'+role+'/cert.pem','/identities/'+role+'/key.pem')
    return c

def opts(role):
    return dict(bootstrap_servers='broker:9093',security_protocol='SSL',ssl_context=tls(role),api_version=(3,9),request_timeout_ms=10000)

def rejected(role,cert=True,trust=True,hostname='broker'):
    try:
        with socket.create_connection(('broker',9093),timeout=5) as s:
            with tls(role,cert,trust).wrap_socket(s,server_hostname=hostname) as ss:
                # TLS 1.3 peut signaler l'absence de certificat seulement au premier read.
                ss.sendall(b'\x00\x00\x00\x00');ss.recv(1)
        raise AssertionError('Expected TLS rejection')
    except (ssl.SSLError,ConnectionResetError): return True

source=Path('/source/PS_20174392719_1491204439457_log.csv')
h=hashlib.sha256()
with source.open('rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
assert h.hexdigest()=='16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b'
with source.open('rb') as f:
    header=next(f);expected=[next(f).rstrip(b'\r\n') for _ in range(1000)]
consumer=KafkaConsumer(group_id='secure-reader',enable_auto_commit=False,session_timeout_ms=6000,consumer_timeout_ms=15000,**opts('consumer'))
tp=TopicPartition('secure.transactions',0);consumer.assign([tp]);start=consumer.end_offsets([tp])[tp];consumer.seek(tp,start)
producer=KafkaProducer(acks='all',**opts('producer'))
for n,value in enumerate(expected):producer.send('secure.transactions',key=str(n).encode(),value=value).get(timeout=10)
producer.flush();got=[]
deadline=time.monotonic()+30
while len(got)<1000 and time.monotonic()<deadline:
    for records in consumer.poll(timeout_ms=500,max_records=1000).values():got.extend(r.value for r in records)
assert got==expected,(len(got),len(expected))
for role in ('producer','intruder'):
    p=KafkaProducer(acks='all',**opts(role))
    try:
        p.send('forbidden',value=b'clearly-labelled-synthetic-negative-fixture').get(timeout=10)
        raise AssertionError('ACL unexpectedly allowed')
    except TopicAuthorizationFailedError: pass
    finally:p.close(timeout=1)
checks={name:rejected('consumer',**kw) for name,kw in [('no_certificate',{'cert':False}),('untrusted_ca',{'trust':False}),('wrong_hostname',{'hostname':'wrong.bc1.test'})]}
with socket.create_connection(('broker',9093),timeout=5) as s:
    with tls('consumer').wrap_socket(s,server_hostname='broker') as ss:version,cipher=ss.version(),ss.cipher()[0]
consumer.close();producer.close()
print(json.dumps(dict(event='kafka_mtls_acl_verified',source_sha256=h.hexdigest(),rows=1000,prefix_equal=True,topic_start_offset=start,tls_version=version,cipher=cipher,negative_tls=checks,producer_forbidden_topic_denied=True,trusted_intruder_denied=True,scope='isolated single-broker test; ZooKeeper plaintext internal; primary pipeline unchanged')))
