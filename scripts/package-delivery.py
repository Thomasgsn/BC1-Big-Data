"""Archiver l'arbre de travail courant sans commit, push ni secrets locaux."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
files=[]
for rel in sorted(set(filter(None,paths))):
    p=root/rel
    if p.is_symlink():raise ValueError('Lien symbolique à examiner avant livraison : '+rel)
    if not p.is_file():continue
    if any(part in {'.git','.env','data','exports','models','volumes','tmp','logs','secrets','__pycache__','target'} or part.startswith('.venv') for part in Path(rel).parts):
        raise ValueError('Fichier exclu détecté dans la sélection Git : '+rel)
    if p.suffix in {'.pem','.key'}:raise ValueError('Identité privée potentielle : '+rel)
    files.append((rel,p))
manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),'candidate':'Thomas Gassmann','scope':'Current working-tree files, including uncommitted changes; not git archive HEAD','base_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'working_tree_modified':bool(subprocess.check_output(['git','status','--porcelain'],cwd=root).strip()),'new_commit_created':False,'pushed':False,'email_sent':False,'excluded':'CSV/weights/exports/volumes/secrets/.git; reference PDFs remain in parent .data and are supplied separately','files':{rel:hashlib.sha256(p.read_bytes()).hexdigest() for rel,p in files}}
out=root/'output';out.mkdir(exist_ok=True);dest=out/f"bc1-rendu-{datetime.now(timezone.utc):%Y%m%d}.zip"
if dest.exists():raise SystemExit(f'{dest.name} existe déjà : archive non écrasée')
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for rel,p in files:archive.write(p,'bc1/'+rel)
    archive.writestr('bc1/DELIVERY-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(dest) as archive:
    assert archive.testzip() is None
    for rel,p in files:
        assert hashlib.sha256(archive.read('bc1/'+rel)).hexdigest()==manifest['files'][rel]
manifest['archive']={'path':'output/'+dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'files':len(files)+1,'crc_and_content_hashes_verified':True}
(out/'delivery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['archive']))
