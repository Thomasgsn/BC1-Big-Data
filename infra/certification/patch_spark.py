"""Maintenance bornée des JAR : téléchargement/validation avant remplacement."""
from pathlib import Path
import hashlib
import json
import re
import os
import tempfile
import urllib.request
import zipfile

folder=Path(os.environ.get('BC1_JARS_DIRECTORY','/opt/spark/jars'))
if folder not in {Path('/opt/spark/jars'),Path('/opt/kafka/libs')}:raise ValueError('Unsupported JAR directory')
lock=Path('/opt/bc1-security/jars.lock.json')
plan=json.loads(lock.read_text())
changed=[]
with tempfile.TemporaryDirectory(prefix='spark-jars-') as temporary:
    verified=[]
    for item in plan['artifacts']:
        filename=item['artifact']+'-'+item['version']+('-'+item['classifier'] if item.get('classifier') else '')+'.jar'
        target=Path(temporary)/filename
        with urllib.request.urlopen(item['url'],timeout=90) as response,target.open('wb') as stream:
            while block:=response.read(1024*1024):stream.write(block)
        algorithm='sha512' if 'sha512' in item else 'sha256'
        if hashlib.new(algorithm,target.read_bytes()).hexdigest()!=item[algorithm]:raise RuntimeError('Artifact digest mismatch: '+filename)
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None:raise RuntimeError('Artifact CRC mismatch: '+filename)
        verified.append((item,target))
    # Le projet n'utilise ni catalogue Hive embarqué ni serveur Thrift/Derby.
    # Ces capacités ne sont pas revendiquées par ce runtime ciblé.
    remove=['netty-*.jar','hadoop-client-api-*.jar','hadoop-client-runtime-*.jar','zookeeper-*.jar','derby-*.jar','jackson-*-asl-*.jar','hive-*.jar','spark-hive*.jar']
    for pattern in remove:
        for p in folder.glob(pattern):
            changed.append({'removed':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});p.unlink()
    for item,path in verified:
        destination=folder/path.name;destination.write_bytes(path.read_bytes());destination.chmod(0o644)
        changed.append({'installed':destination.name,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
Path('/opt/bc1-security/jars-inventory.json').write_text(json.dumps({'lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),'changes':changed,'claims':'Runtime filesystem only; no claim of erasing parent image layers or complete vulnerability remediation'},indent=2)+'\n')
print(json.dumps({'event':'spark_jars_maintained','changes':len(changed)}))
