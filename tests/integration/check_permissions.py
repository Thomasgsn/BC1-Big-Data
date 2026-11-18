"""Tests réels d'accès et révocation sur une identité de test dédiée, jamais un compte utilisateur."""

import hashlib
import json
import os
import secrets
import urllib.request
import urllib.error
from uuid import uuid4

import psycopg
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from rncp_bc1.api import connect_sql, mongo


def main():
    identifier, token = "AUTOMATED_REVOCATION_TEST_"+uuid4().hex, secrets.token_urlsafe(32)
    with psycopg.connect(host="postgres", dbname="bc1", user="bc1owner", password=os.environ["POSTGRES_PASSWORD"], connect_timeout=3) as admin:
        admin.execute("INSERT INTO api_principal (principal_id,role,token_hash,active) VALUES (%s,'reader',%s,true)",
                      (identifier, hashlib.sha256(token.encode()).hexdigest()))
    request = urllib.request.Request("http://api:8000/v1/alerts?limit=1", headers={"Authorization": "Bearer "+token})
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            assert reply.status == 200
    finally:
        # Révoquer aussi si le contrôle positif échoue ; l'identité de test reste inactive.
        with psycopg.connect(host="postgres", dbname="bc1", user="bc1owner", password=os.environ["POSTGRES_PASSWORD"], connect_timeout=3) as admin:
            admin.execute("UPDATE api_principal SET active=false WHERE principal_id=%s", (identifier,))
    try:
        urllib.request.urlopen(request, timeout=10)
        raise AssertionError("Jeton révoqué accepté")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    with connect_sql() as conn:
        for table, action in [("api_principal", "INSERT"), ("api_principal", "UPDATE"), ("analyst_decision", "UPDATE"), ("analyst_decision", "DELETE")]:
            allowed = conn.execute("SELECT has_table_privilege(current_user,%s,%s) AS allowed", (table, action)).fetchone()["allowed"]
            assert not allowed, (table, action)
    try:
        psycopg.connect(host="postgres", dbname="bc1", user="bc1app", password="INVALID_AUTOMATED_TEST_PASSWORD", connect_timeout=3)
        raise AssertionError("Mot de passe SQL invalide accepté")
    except psycopg.OperationalError:
        pass
    mongo().fraud_scores.find_one({}, {"_id": 1})
    for client in [MongoClient("mongo", serverSelectionTimeoutMS=3000),
                   MongoClient("mongo", username="bc1app", password="INVALID_AUTOMATED_TEST_PASSWORD", authSource="fraud", serverSelectionTimeoutMS=3000)]:
        try:
            client.fraud.fraud_scores.find_one({})
            raise AssertionError("Accès Mongo non autorisé accepté")
        except OperationFailure as error:
            assert error.code in [13, 18]
        finally:
            client.close()
    print(json.dumps({"event": "permissions_verified", "token_active_status": 200, "token_revoked_status": 401,
                      "sql_immutable_decisions": True, "sql_identity_write_denied": True,
                      "sql_wrong_password_denied": True, "mongo_anonymous_and_wrong_password_denied": True,
                      "fixture": "dedicated test principal retained inactive; no existing account changed",
                      "limitations": "HDFS/Kafka/Spark strong authentication and TLS not tested or configured"}))


if __name__ == "__main__":
    main()
