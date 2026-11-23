"""Configuration explicite des transports, partagée par les jobs et l'API."""

import os
from pathlib import Path
import ssl
from urllib.parse import quote


def producer_tls_options() -> dict:
    folder = os.environ.get("BC1_KAFKA_TLS_DIR")
    if not folder:
        return {}
    root = Path(folder)
    context = ssl.create_default_context(cafile=str(root / "ca.crt"))
    context.load_cert_chain(str(root / "cert.pem"), str(root / "key.pem"))
    return {"security_protocol": "SSL", "ssl_context": context}


def kafka_stream_options() -> dict:
    filename = os.environ.get("BC1_KAFKA_TLS_PROPERTIES")
    if not filename:
        return {}
    path = Path(filename)
    if path.stat().st_size > 16384:
        raise ValueError("Configuration TLS Kafka trop grande.")
    allowed = {"security.protocol", "ssl.keystore.type", "ssl.keystore.location",
               "ssl.keystore.password", "ssl.key.password", "ssl.truststore.type",
               "ssl.truststore.location", "ssl.truststore.password", "ssl.endpoint.identification.algorithm"}
    properties = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in allowed or key in properties:
            raise ValueError("Propriété TLS Kafka inconnue ou dupliquée.")
        properties[key] = value
    if properties.get("security.protocol") != "SSL" or properties.get("ssl.endpoint.identification.algorithm") != "https":
        raise ValueError("TLS Kafka et validation du nom de serveur requis.")
    required = allowed - {"ssl.key.password"}
    if required - properties.keys():
        raise ValueError("Configuration TLS Kafka incomplète.")
    return {"kafka." + key: value for key, value in properties.items()}


def sql_tls_options() -> dict:
    ca = os.environ.get("BC1_DB_TLS_CA")
    return {"sslmode": "verify-full", "sslrootcert": ca} if ca else {}


def mongo_tls_options() -> dict:
    ca = os.environ.get("BC1_DB_TLS_CA")
    return {"tls": True, "tlsCAFile": ca} if ca else {}


def mongo_spark_uri(password: str) -> str:
    tls = "&tls=true" if os.environ.get("BC1_DB_TLS_CA") else ""
    return "mongodb://bc1app:" + quote(password, safe="") + "@mongo:27017/fraud?authSource=fraud" + tls


def jdbc_sql_url() -> str:
    ca = os.environ.get("BC1_DB_TLS_CA")
    return "jdbc:postgresql://postgres:5432/bc1" + ("?sslmode=verify-full&sslrootcert=" + quote(ca, safe="/") if ca else "")
