#!/usr/bin/env python3
"""Diagnostic reproductible ; ne crée pas de service ni de volume persistant."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(arguments, timeout=30):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)
        return {"command": arguments, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": arguments, "returncode": None, "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-images", action="store_true", help="Télécharger et sonder les images épinglées")
    parser.add_argument("--actor", choices=["terminal", "codex"], default="terminal")
    args = parser.parse_args()
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "actor": args.actor,
              "platform": platform.platform(), "python": platform.python_version(),
              "disk_free_bytes": shutil.disk_usage(ROOT).free,
              "scope": "Environnement et images seulement ; pas de compatibilité interservices validée.",
              "gephi_application_found": any(p.exists() for p in [Path('/Applications/Gephi.app'), Path.home()/'Applications/Gephi.app']),
              "checks": []}
    checks = report["checks"]
    info = run(["docker", "info", "--format", "{{json .}}"])
    # La réponse complète peut contenir des proxys ou des configurations privées.
    # Ne conserver qu'une sélection de propriétés matérielles non sensibles.
    raw_info = info.pop("stdout", "")
    if info["returncode"] == 0:
        try:
            parsed = json.loads(raw_info)
            info["server"] = {key: parsed.get(key) for key in ["ServerVersion", "OperatingSystem", "Architecture", "NCPU", "MemTotal"]}
        except json.JSONDecodeError:
            info["returncode"] = 1
            info["error"] = "Réponse docker info non JSON"
    checks.append(info)
    available = info["returncode"] == 0
    if available:
        checks.append(run(["docker", "run", "--rm", "--pull=missing", "hello-world@sha256:1e4c05b897a751332ce85c7e9449da2d93514ea2dea6dbb0e2753c9e949b2bfa"], timeout=180))
    if available and args.probe_images:
        images = json.loads((ROOT/"infra/images.lock.json").read_text())["images"]
        commands = {
            "spark": ["sh", "-c", "/opt/spark/bin/spark-submit --version && python3 --version && java -version"],
            "kafka": ["sh", "-c", "test -f /opt/kafka/bin/zookeeper-server-start.sh && /opt/kafka/bin/kafka-topics.sh --version && java -version"],
            "hadoop": ["sh", "-c", "hdfs version && java -version && id"],
            "postgres": ["postgres", "--version"],
            "mongo": ["mongod", "--version"],
            "python": ["python", "--version"],
            "ollama": ["ollama", "--version"],
            "maven": ["mvn", "--version"],
        }
        for name, image in images.items():
            print(f"Sonde image : {name}", flush=True)
            pulled = run(["docker", "pull", image["reference"]], timeout=900)
            checks.append(pulled)
            if pulled["returncode"] != 0:
                continue
            checks.append(run(["docker", "run", "--rm", "--network", "none", "--memory", "1g",
                               "--entrypoint", commands[name][0], image["reference"], *commands[name][1:]], timeout=120))
    success = all(check["returncode"] == 0 for check in checks)
    report["status"] = "passed" if success else "blocked_or_failed"
    output = ROOT / f"docs/evidence/p1/environment-{args.actor}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    print(f"Diagnostic : {report['status']} ; rapport : {output.relative_to(ROOT)}")
    if not available:
        print("Moteur Docker inaccessible depuis ce processus ; aucune sonde de conteneur exécutée.", file=sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
