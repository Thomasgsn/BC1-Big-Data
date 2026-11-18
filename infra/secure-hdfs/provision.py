"""Initialiser un royaume et des identités propres au laboratoire sécurisé.

Les clés privées restent dans des volumes Docker distincts, jamais dans le dépôt.
Les renouvellements/reprises conservent les clés et la base Kerberos existantes.
"""

import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import xml.etree.ElementTree as ET

REALM = "BC1.TEST"
DB = Path("/kdc")
ROLES = {"namenode": ["nn/namenode.bc1.test", "HTTP/namenode.bc1.test"],
         "datanode": ["dn/datanode.bc1.test", "HTTP/datanode.bc1.test"],
         "admin": ["hadoop"], "alice": ["alice"], "bob": ["bob"]}


def command(*args, input_text=None):
    result = subprocess.run(args, input=input_text, text=True, capture_output=True, timeout=90)
    if result.returncode:
        # Les arguments ne contiennent que des chemins/principaux, aucun secret.
        raise RuntimeError(f"Commande échouée : {args[0]} : {result.stderr[-1500:]}")
    return result.stdout


def xml(path, values):
    root = ET.Element("configuration")
    for name, value in values.items():
        prop = ET.SubElement(root, "property")
        ET.SubElement(prop, "name").text = name
        ET.SubElement(prop, "value").text = str(value)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main():
    os.umask(0o077)
    DB.mkdir(exist_ok=True)
    krb = f"""[libdefaults]
 default_realm = {REALM}
 dns_lookup_kdc = false
 dns_lookup_realm = false
 rdns = false
 dns_canonicalize_hostname = false
 udp_preference_limit = 1
 ticket_lifetime = 1h
 renew_lifetime = 1d
 permitted_enctypes = aes256-cts-hmac-sha1-96 aes128-cts-hmac-sha1-96
[realms]
 {REALM} = {{
  kdc = kdc.bc1.test:88
 }}
[domain_realm]
 .bc1.test = {REALM}
 bc1.test = {REALM}
"""
    (DB/"krb5.conf").write_text(krb)
    (DB/"kdc.conf").write_text(f"""[kdcdefaults]
 kdc_ports = 88
 kdc_tcp_ports = 88
[realms]
 {REALM} = {{
  database_name = /kdc/principal
  key_stash_file = /kdc/stash
  max_life = 1h
  max_renewable_life = 1d
  supported_enctypes = aes256-cts-hmac-sha1-96:normal aes128-cts-hmac-sha1-96:normal
 }}
""")
    os.environ["KRB5_CONFIG"] = str(DB/"krb5.conf")
    os.environ["KRB5_KDC_PROFILE"] = str(DB/"kdc.conf")
    if not (DB/"principal").exists():
        password = secrets.token_urlsafe(48)
        command("kdb5_util", "create", "-s", "-r", REALM, input_text=password+"\n"+password+"\n")
    if not (DB/"ca.key").exists():
        command("openssl", "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-days", "365",
                "-subj", "/CN=BC1 isolated HDFS root", "-keyout", str(DB/"ca.key"), "-out", str(DB/"ca.crt"))
    core = {"fs.defaultFS": "hdfs://namenode.bc1.test:8020",
            "hadoop.security.authentication": "kerberos", "hadoop.security.authorization": "true",
            "hadoop.rpc.protection": "privacy", "ipc.client.fallback-to-simple-auth-allowed": "false",
            "hadoop.security.auth_to_local": "RULE:[2:$1](nn|dn|HTTP)s/.*/hadoop/\nDEFAULT",
            "hadoop.http.filter.initializers": "org.apache.hadoop.security.AuthenticationFilterInitializer",
            "hadoop.http.authentication.type": "kerberos",
            "hadoop.http.authentication.kerberos.principal": f"HTTP/_HOST@{REALM}",
            "hadoop.http.authentication.kerberos.keytab": "/etc/bc1/service.keytab",
            "hadoop.http.authentication.signature.secret.file": "/etc/bc1/http-signature.secret",
            "hadoop.http.authentication.simple.anonymous.allowed": "false",
            "hadoop.http.authentication.token.validity": "600",
            "hadoop.ssl.server.conf": "ssl-server.xml", "hadoop.ssl.client.conf": "ssl-client.xml",
            "hadoop.security.crypto.codec.classes.aes.ctr.nopadding": "org.apache.hadoop.crypto.JceAesCtrCryptoCodec",
            "hadoop.ssl.enabled.protocols": "TLSv1.2,TLSv1.3"}
    hdfs = {"dfs.namenode.rpc-address": "namenode.bc1.test:8020",
            "dfs.namenode.name.dir": "file:///data/name", "dfs.datanode.data.dir": "file:///data/data",
            "dfs.replication": "1", "dfs.permissions.enabled": "true", "dfs.block.access.token.enable": "true",
            "dfs.namenode.kerberos.principal": f"nn/namenode.bc1.test@{REALM}",
            "dfs.namenode.keytab.file": "/etc/bc1/service.keytab",
            "dfs.datanode.kerberos.principal": f"dn/datanode.bc1.test@{REALM}",
            "dfs.datanode.keytab.file": "/etc/bc1/service.keytab",
            "dfs.namenode.kerberos.internal.spnego.principal": f"HTTP/namenode.bc1.test@{REALM}",
            "dfs.web.authentication.kerberos.principal": f"HTTP/_HOST@{REALM}",
            "dfs.web.authentication.kerberos.keytab": "/etc/bc1/service.keytab",
            "dfs.http.policy": "HTTPS_ONLY", "dfs.namenode.https-address": "namenode.bc1.test:9871",
            "dfs.datanode.https.address": "datanode.bc1.test:9865",
            "dfs.datanode.address": "0.0.0.0:9866", "dfs.datanode.hostname": "datanode.bc1.test",
            "dfs.namenode.datanode.registration.ip-hostname-check": "false",
            "dfs.client.use.datanode.hostname": "true", "dfs.datanode.use.datanode.hostname": "true",
            "dfs.data.transfer.protection": "privacy", "dfs.encrypt.data.transfer": "true",
            "dfs.encrypt.data.transfer.cipher.suites": "AES/CTR/NoPadding",
            "dfs.encrypt.data.transfer.cipher.key.bitlength": "256"}
    for role, principals in ROLES.items():
        folder = Path("/roles")/role
        folder.mkdir(exist_ok=True)
        if not (folder/"service.keytab").exists():
            for principal in principals:
                command("kadmin.local", "-r", REALM, "-q", f"addprinc -randkey {principal}@{REALM}")
                command("kadmin.local", "-r", REALM, "-q", f"ktadd -k {folder}/service.keytab {principal}@{REALM}")
        (folder/"krb5.conf").write_text(krb)
        (folder/"principal.txt").write_text(principals[0]+"@"+REALM+"\n")
        (folder/"ca.crt").write_bytes((DB/"ca.crt").read_bytes())
        xml(folder/"core-site.xml", core)
        xml(folder/"hdfs-site.xml", hdfs)
        if not (folder/"http-signature.secret").exists():
            (folder/"http-signature.secret").write_text(secrets.token_urlsafe(64))
        (folder/"log4j.properties").write_text(
            "log4j.rootLogger=WARN,console\n"
            "log4j.appender.console=org.apache.log4j.ConsoleAppender\n"
            "log4j.appender.console.target=System.err\n"
            "log4j.appender.console.layout=org.apache.log4j.PatternLayout\n"
            "log4j.appender.console.layout.ConversionPattern=%d{ISO8601} %-5p %c{1}: %m%n\n")
        if not (folder/"store.pass").exists():
            (folder/"store.pass").write_text(secrets.token_urlsafe(32))
        password = (folder/"store.pass").read_text()
        if role in {"namenode", "datanode"} and not (folder/"server.p12").exists():
            host = role+".bc1.test"
            command("openssl", "req", "-new", "-newkey", "rsa:3072", "-nodes", "-subj", "/CN="+host,
                    "-keyout", str(folder/"server.key"), "-out", str(folder/"server.csr"))
            ext = folder/"certificate.ext"
            ext.write_text(f"subjectAltName=DNS:{host}\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n")
            command("openssl", "x509", "-req", "-in", str(folder/"server.csr"), "-CA", str(DB/"ca.crt"),
                    "-CAkey", str(DB/"ca.key"), "-CAcreateserial", "-days", "90", "-extfile", str(ext),
                    "-out", str(folder/"server.crt"))
            command("openssl", "pkcs12", "-export", "-name", role, "-inkey", str(folder/"server.key"),
                    "-in", str(folder/"server.crt"), "-certfile", str(DB/"ca.crt"),
                    "-out", str(folder/"server.p12"), "-passout", "file:"+str(folder/"store.pass"))
        if not (folder/"trust.p12").exists():
            command("keytool", "-importcert", "-noprompt", "-alias", "bc1-ca", "-file", str(folder/"ca.crt"),
                    "-keystore", str(folder/"trust.p12"), "-storetype", "PKCS12",
                    "-storepass:file", str(folder/"store.pass"))
        xml(folder/"ssl-server.xml", {"ssl.server.keystore.location": "/etc/bc1/server.p12",
            "ssl.server.keystore.type": "PKCS12", "ssl.server.keystore.password": password,
            "ssl.server.keystore.keypassword": password, "ssl.server.truststore.location": "/etc/bc1/trust.p12",
            "ssl.server.truststore.type": "PKCS12", "ssl.server.truststore.password": password})
        xml(folder/"ssl-client.xml", {"ssl.client.truststore.location": "/etc/bc1/trust.p12",
            "ssl.client.truststore.type": "PKCS12", "ssl.client.truststore.password": password})
        for path in folder.iterdir():
            os.chown(path, 1000, 1000)
            path.chmod(0o400)
        os.chown(folder, 1000, 1000)
        folder.chmod(0o500)
    for name in ["name", "data"]:
        path = Path("/storage")/name
        path.mkdir(exist_ok=True)
        os.chown(path, 1000, 1000)
        path.chmod(0o700)
    certificate = command("openssl", "x509", "-in", str(DB/"ca.crt"), "-noout", "-fingerprint", "-sha256").strip()
    inventory = command("dpkg-query", "-W", "-f=${Package}=${Version}\n")
    report = {"event": "secure_hdfs_provisioned", "realm": REALM, "roles": list(ROLES),
              "ca_certificate_sha256": certificate, "packages": inventory.splitlines(),
              "provision_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "keys_in_docker_volumes_only": True, "human_users": False}
    (DB/"public-manifest.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({key: value for key, value in report.items() if key != "packages"}))


if __name__ == "__main__":
    main()
