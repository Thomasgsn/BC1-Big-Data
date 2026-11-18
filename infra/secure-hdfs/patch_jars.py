"""Construire le runtime HDFS à partir des remplacements Maven verrouillés.

Ne s'exécute qu'au build d'image ; aucun volume utilisateur n'est monté.
Les distributions client-minicluster/YARN inutilisées embarquent d'autres copies
vulnérables. L'archive source Apache reste intacte hors de cette image dérivée.
"""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request
import zipfile


def main():
    lock = json.loads(Path("/opt/bc1-build/jars.lock.json").read_text())
    root = Path("/opt/hadoop/share/hadoop")
    for optional in lock["removed_optional_distributions"]:
        if optional not in {"client", "yarn"}:
            raise ValueError("Distribution hors périmètre")
        if (root/optional).exists():
            shutil.rmtree(root/optional)
        (root/optional).mkdir()
    grouped = defaultdict(list)
    for artifact in lock["artifacts"]:
        grouped[artifact["artifact"]].append(artifact)
    inventory = []
    with tempfile.TemporaryDirectory(prefix="bc1-jars-") as tmp:
        for artifact, copies in grouped.items():
            targets = [folder for folder in [root/"common/lib", root/"hdfs/lib"]
                       if any(re.fullmatch(re.escape(artifact)+r"-\d.*\.jar", p.name) for p in folder.iterdir())]
            if not targets:
                raise RuntimeError("Artefact d'origine absent : "+artifact)
            downloaded = []
            for item in copies:
                url = item["url"]
                if not url.startswith("https://repo.maven.apache.org/maven2/"):
                    raise ValueError("Origine Maven non autorisée")
                name = url.rsplit("/", 1)[-1]
                if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.jar", name):
                    raise ValueError("Nom d'artefact invalide")
                path = Path(tmp)/name
                with urllib.request.urlopen(url, timeout=60) as response, path.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
                with path.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha512").hexdigest() != item["sha512"]:
                        raise ValueError("SHA-512 invalide : "+name)
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        raise ValueError("JAR corrompu : "+name)
                downloaded.append(path)
            for folder in targets:
                for old in folder.iterdir():
                    if re.fullmatch(re.escape(artifact)+r"-\d.*\.jar", old.name):
                        old.unlink()
                for path in downloaded:
                    target = folder/path.name
                    shutil.copyfile(path, target)
                    inventory.append({"path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                      "artifact": artifact, "version": copies[0]["version"]})
    Path("/opt/bc1").mkdir(exist_ok=True)
    Path("/opt/bc1/jars-inventory.json").write_text(json.dumps(inventory, indent=2)+"\n")
    print(json.dumps({"event": "hdfs_dependency_maintenance", "jar_copies": len(inventory),
                      "versions": {key: lock[key] for key in ["netty_version", "bc_version", "jsch_version"]}}))


if __name__ == "__main__":
    main()
