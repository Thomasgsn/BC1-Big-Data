"""Contrôles réels Kerberos, permissions, chiffrement et CA du laboratoire HDFS."""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import urllib.error
import urllib.request

REMOTE = "/bc1/private/paysim-prefix.csv"


def run(*args, success=True, env=None):
    result = subprocess.run(args, capture_output=True, timeout=60, env=env)
    if success and result.returncode:
        raise AssertionError(f"Commande autorisée refusée : {args[0]} : {result.stderr.decode(errors='replace')[-1000:]}")
    if not success and result.returncode == 0:
        raise AssertionError(f"Commande interdite acceptée : {args[0]}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unauthorized", action="store_true")
    args = parser.parse_args()
    principal = Path("/etc/bc1/principal.txt").read_text().strip()
    if Path("/tmp/krb5cc_1000").exists():
        run("kdestroy", "-A")
    spoof = dict(os.environ, HADOOP_USER_NAME="hadoop")
    denied = run("hdfs", "dfs", "-ls", "/bc1", success=False, env=spoof)
    if not any(word in denied.stderr.lower() for word in [b"kerberos", b"credentials", b"authenticate"]):
        raise AssertionError("L'échec sans ticket n'est pas attribuable à l'authentification")
    run("kinit", "-kt", "/etc/bc1/service.keytab", principal)
    if args.unauthorized:
        denied = run("hdfs", "dfs", "-cat", REMOTE, success=False)
        if b"permission denied" not in denied.stderr.lower():
            raise AssertionError("Refus non attribuable aux permissions HDFS")
        print(json.dumps({"event": "secure_hdfs_unauthorized_verified", "principal": principal,
                          "no_ticket_and_username_spoof_refused": True,
                          "valid_ticket_private_data_refused": True, "synthetic_service_identity": True}))
        return 0
    source = Path("/data/raw/PS_20174392719_1491204439457_log.csv")
    with source.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b":
            raise AssertionError("PaySim non conforme à l'empreinte source")
    with source.open(newline="") as stream:
        reader = csv.reader(stream)
        rows = [next(reader) for _ in range(1001)]
    content = io.StringIO(newline="")
    csv.writer(content).writerows(rows)
    payload = content.getvalue().encode()
    local = Path("/tmp/paysim-prefix.csv")
    local.write_bytes(payload)
    exists = subprocess.run(["hdfs", "dfs", "-test", "-e", REMOTE], capture_output=True, timeout=30)
    if exists.returncode:
        run("hdfs", "dfs", "-put", str(local), REMOTE)
    actual = run("hdfs", "dfs", "-cat", REMOTE).stdout
    if actual != payload:
        raise AssertionError("Contenu HDFS différent du préfixe réel PaySim")
    via_https = run("hdfs", "dfs", "-fs", "swebhdfs://namenode.bc1.test:9871", "-cat", REMOTE).stdout
    if via_https != payload:
        raise AssertionError("Contenu HTTPS/SPNEGO différent du préfixe PaySim")
    weak = run("hdfs", "dfs", "-Dhadoop.rpc.protection=authentication", "-ls", "/bc1", success=False)
    if not any(word in weak.stderr.lower() for word in [b"protection", b"sasl", b"quality", b"qop"]):
        raise AssertionError("Le refus RPC faible n'est pas attribuable à la protection SASL")
    host = "namenode.bc1.test"
    context = ssl.create_default_context(cafile="/etc/bc1/ca.crt")
    with socket.create_connection((host, 9871), timeout=5) as transport:
        with context.wrap_socket(transport, server_hostname=host) as secured:
            version = secured.version()
            cipher = secured.cipher()[0]
            fingerprint = hashlib.sha256(secured.getpeercert(binary_form=True)).hexdigest()
    try:
        with socket.create_connection((host, 9871), timeout=5) as transport:
            ssl.create_default_context().wrap_socket(transport, server_hostname=host)
    except ssl.SSLCertVerificationError:
        pass
    else:
        raise AssertionError("CA locale acceptée sans confiance explicite")
    try:
        with socket.create_connection((host, 9871), timeout=5) as transport:
            context.wrap_socket(transport, server_hostname="artificial-wrong-host.bc1.test")
    except ssl.SSLCertVerificationError:
        pass
    else:
        raise AssertionError("Mauvais nom de serveur accepté")
    try:
        urllib.request.urlopen("https://"+host+":9871/", context=context, timeout=10)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise AssertionError(f"Code HTTP anonyme inattendu : {error.code}") from error
    else:
        raise AssertionError("Interface HDFS anonyme accessible")
    print(json.dumps({"event": "secure_hdfs_authorized_verified", "principal": principal,
                      "dataset_rows": 1000, "csv_bytes": len(payload),
                      "payload_sha256": hashlib.sha256(payload).hexdigest(),
                      "no_ticket_and_username_spoof_refused": True,
                      "authorized_write_read_exact": True, "weak_rpc_protection_refused": True,
                      "authorized_https_spnego_read_exact": True,
                      "tls_version": version, "tls_cipher": cipher, "server_certificate_sha256": fingerprint,
                      "untrusted_ca_refused": True, "wrong_hostname_refused": True,
                      "anonymous_https_status": 401,
                      "scope": "real isolated HDFS; synthetic service identity; actual PaySim prefix; no production claim"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
