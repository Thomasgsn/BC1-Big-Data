"""Contrôles autorisés/refusés sur les vrais services du profil de certification."""
import json
import os
import socket
import ssl
import urllib.error
import urllib.request
import psycopg
from pymongo import MongoClient
from pymongo.errors import PyMongoError

ca=os.environ['BC1_DB_TLS_CA'];pgpass=os.environ['POSTGRES_APP_PASSWORD'];mongopass=os.environ['MONGO_APP_PASSWORD']
pg=dict(host='postgres',dbname='bc1',user='bc1app',password=pgpass,connect_timeout=4)
with psycopg.connect(**pg,sslmode='verify-full',sslrootcert=ca) as conn:
    with conn.cursor() as c:
        c.execute('SELECT ssl,version,cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid()');pg_ssl=c.fetchone()
        assert pg_ssl[0]
checks={}
for name,extra in [('postgres_plaintext',{'sslmode':'disable'}),('postgres_wrong_hostname',{'host':'wrong.bc1.test','hostaddr':socket.gethostbyname('postgres'),'sslmode':'verify-full','sslrootcert':ca}),('postgres_wrong_password',{'password':'explicit-synthetic-invalid-password','sslmode':'verify-full','sslrootcert':ca})]:
    try:
        with psycopg.connect(**(pg|extra)):pass
        raise AssertionError('Expected rejection '+name)
    except psycopg.OperationalError:checks[name]=True
base=dict(host='mongo',username='bc1app',password=mongopass,authSource='fraud',serverSelectionTimeoutMS=2500,connectTimeoutMS=2000)
with MongoClient(**base,tls=True,tlsCAFile=ca) as client:collections=client.fraud.list_collection_names();assert 'fraud_scores' in collections
for name,extra in [('mongo_plaintext',{'tls':False}),('mongo_untrusted_ca',{'tls':True}),('mongo_wrong_password',{'password':'explicit-synthetic-invalid-password','tls':True,'tlsCAFile':ca})]:
    try:
        with MongoClient(**(base|extra)) as client:client.fraud.list_collection_names()
        raise AssertionError('Expected rejection '+name)
    except PyMongoError:checks[name]=True
context=ssl.create_default_context(cafile=ca)
with socket.create_connection(('api',8443),timeout=5) as s:
    with context.wrap_socket(s,server_hostname='api') as ss:api_tls={'version':ss.version(),'cipher':ss.cipher()[0]}
try:urllib.request.urlopen('https://api:8443/v1/alerts',context=context,timeout=8);raise AssertionError('Missing bearer accepted')
except urllib.error.HTTPError as e:assert e.code==401;checks['api_missing_token']=True
try:urllib.request.urlopen('https://api:8443/health/live',context=ssl.create_default_context(),timeout=5);raise AssertionError('Untrusted CA accepted')
except urllib.error.URLError as e:assert isinstance(e.reason,ssl.SSLCertVerificationError);checks['api_untrusted_ca']=True
print(json.dumps({'event':'integrated_security_verified','postgres_tls':{'enabled':pg_ssl[0],'version':pg_ssl[1],'cipher':pg_ssl[2]},'api_tls':api_tls,'mongo_tls_authenticated':True,'refused':checks,'scope':'Live certification services; negative passwords are explicit fixtures, no production risk acceptance'}))
