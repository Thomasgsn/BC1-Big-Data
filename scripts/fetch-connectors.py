"""Acquisition et contrôle des connecteurs verrouillés, sans secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request
import zipfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--lock',type=Path,required=True)
parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--check-only',action='store_true')
args=parser.parse_args();lock=json.loads(args.lock.read_text());args.directory.mkdir(parents=True,exist_ok=True)
expected={a['filename'] for a in lock['artifacts']}
for item in lock['artifacts']:
    name=item['filename']
    if Path(name).name!=name or not item['url'].startswith('https://repo.maven.apache.org/maven2/'):
        raise ValueError('Invalid connector lock')
    target=args.directory/name
    if not target.exists():
        if args.check_only:raise FileNotFoundError('Missing locked connector: '+name)
        with tempfile.NamedTemporaryFile(dir=args.directory,delete=False) as stream:
            temp=Path(stream.name)
            try:
                with urllib.request.urlopen(item['url'],timeout=90) as response:
                    size=0
                    while block:=response.read(1024*1024):
                        size+=len(block)
                        if size>64*1024*1024:raise ValueError('Connector exceeds size bound')
                        stream.write(block)
                stream.flush();os.fsync(stream.fileno())
                if hashlib.sha256(temp.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Connector digest mismatch: '+name)
                with zipfile.ZipFile(temp) as archive:
                    if archive.testzip() is not None:raise ValueError('Connector archive corrupt: '+name)
                temp.chmod(0o644);os.link(temp,target)
            finally:temp.unlink(missing_ok=True)
    if target.resolve().parent!=args.directory.resolve() or hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError('Existing connector mismatch: '+name)
if {p.name for p in args.directory.glob('*.jar')}!=expected:raise ValueError('Unexpected extra connector JAR')
print(json.dumps({'event':'locked_connectors_verified','files':len(expected),'check_only':args.check_only}))
