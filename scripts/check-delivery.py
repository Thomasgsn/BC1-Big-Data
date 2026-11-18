"""Vérifie le dossier local sans afficher les valeurs des secrets."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

root=Path(__file__).resolve().parents[1]
files=[root/x for x in subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0') if x]
secrets=[]
for line in (root/'.env').read_text().splitlines():
    if '=' not in line or line.lstrip().startswith('#'):continue
    key,value=line.split('=',1);value=value.strip().strip('\"').strip("'")
    if re.search(r'PASSWORD|TOKEN|SECRET',key) and len(value)>=12:secrets.append((key,value))
errors=[];count={'python':0,'json':0,'markdown_links':0,'files':len(files)};manifest={}
for p in files:
    rel=str(p.relative_to(root))
    if any(x in p.parts for x in ('__pycache__','target')):continue
    try:text=p.read_text()
    except (UnicodeError,IsADirectoryError):continue
    for key,value in secrets:
        if value in text:errors.append({'kind':'exact_secret_value','file':rel,'variable':key})
    if re.search(r'-----BEGIN (?:RSA )?PRIVATE KEY-----\s*\n[A-Za-z0-9+/=]{20}', text):errors.append({'kind':'private_key','file':rel})
    if p.suffix=='.py':ast.parse(text,filename=rel);count['python']+=1
    if p.suffix=='.json':json.loads(text);count['json']+=1
    if p.suffix=='.md':
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            if re.match(r'\w+://|mailto:|#',target):continue
            target=unquote(target.split('#')[0].strip('<>'))
            if not target:continue
            count['markdown_links']+=1
            if not (p.parent/target).exists():errors.append({'kind':'broken_link','file':rel,'target':target})
    if rel.startswith(('src/','scripts/','tests/','infra/')) or rel in ('.dockerignore','.env.example','.gitignore','docker-compose.yml','Makefile','pyproject.toml','requirements-api.in','requirements-api.lock','requirements-runtime.txt'):
        manifest[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
now=datetime.now(timezone.utc).isoformat();mp=root/'docs/evidence/source-code-manifest.json'
previous=json.loads(mp.read_text()) if mp.exists() else None
if previous and previous.get('files')!=manifest:
    dest=root/'docs/evidence/source-code-manifest-pre-finalization.json'
    if not dest.exists():dest.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n')
mp.write_text(json.dumps({'created_at_utc':now,'scope':'Local runtime source, tests, tooling and public configuration; excludes secrets, data, builds, rendered artifacts and prose; not a published Git revision','files':manifest},ensure_ascii=False,indent=2)+'\n')
result={'created_at_utc':now,'checks':count,'source_manifest_files':len(manifest),'exact_secret_values_checked':len(secrets),'secret_scan_scope':'Exact values from local .env and private-key markers in nonignored text; not a general security scanner','errors':errors,'status':'passed' if not errors else 'failed'}
(root/'docs/evidence/p9/local-delivery-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));raise SystemExit(bool(errors))
