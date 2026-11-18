"""Tests HTTP réels contre l'API/SQL/Mongo ; les décisions de test sont identifiées."""

import json
from concurrent.futures import ThreadPoolExecutor
import os
import unittest
import urllib.error
import urllib.request
from uuid import uuid4

BASE = "http://api:8000"


class ApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = os.environ["API_TOKEN_READER"]
        cls.analyst = os.environ["API_TOKEN_ANALYST"]

    def request(self, path, token=None, method="GET", body=None, extra_headers=None):
        headers = dict(extra_headers or {})
        if token:
            headers["Authorization"] = "Bearer "+token
        payload = None if body is None else json.dumps(body).encode()
        if payload:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(BASE+path, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=130) as response:
                status, raw, response_headers = response.status, response.read(2_000_000), response.headers
        except urllib.error.HTTPError as error:
            status, raw, response_headers = error.code, error.read(2_000_000), error.headers
        text = raw.decode()
        if self.reader in text or self.analyst in text:
            self.fail("Une réponse divulgue un jeton.")
        return status, json.loads(text), response_headers

    def test_a_health_and_documented_contract(self):
        self.assertEqual(self.request("/health/ready")[0], 200)
        status, schema, _ = self.request("/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("/v1/alerts", schema["paths"])
        self.assertIn("HTTPBearer", schema["components"]["securitySchemes"])

    def test_b_authentication_and_authorization(self):
        self.assertEqual(self.request("/v1/alerts")[0], 401)
        self.assertEqual(self.request("/v1/alerts", "x"*43)[0], 401)
        self.assertEqual(self.request("/v1/alerts/"+"0"*64+"/cases", self.reader, "POST")[0], 403)

    def test_c_actual_data_lab_and_bounds(self):
        status, body, _ = self.request("/v1/graph/exports", self.reader)
        self.assertEqual(status, 200)
        self.assertTrue(any(x["snapshot_id"] == "runtime-v1-steps-1-1" for x in body["items"]))
        self.assertEqual(self.request("/v1/metrics?limit=101", self.reader)[0], 422)
        self.assertEqual(self.request("/v1/alerts?offset=10001", self.reader)[0], 422)
        self.assertEqual(self.request("/v1/alerts/not-a-hash", self.reader)[0], 422)
        self.assertEqual(self.request("/v1/alerts/"+"0"*64, self.reader)[0], 404)

    def test_d_unknown_case_and_invalid_decision(self):
        headers = {"Idempotency-Key": str(uuid4())}
        body = {"outcome": "uncertain", "reason": "[TEST AUTOMATIQUE] Cas inexistant", "origin": "automated_test"}
        self.assertEqual(self.request("/v1/cases/"+str(uuid4())+"/decisions", self.analyst, "POST", body, headers)[0], 404)
        body["reason"] = " "
        self.assertEqual(self.request("/v1/cases/"+str(uuid4())+"/decisions", self.analyst, "POST", body, headers)[0], 422)

    def test_e_decision_persistence_and_idempotency(self):
        status, alerts, _ = self.request("/v1/alerts?limit=1", self.analyst)
        self.assertEqual(status, 200)
        if not alerts["items"]:
            self.skipTest("Aucun scoring modèle encore publié ; décision positive non testée.")
        identifier = alerts["items"][0]["transaction_id"]
        status, case, _ = self.request(f"/v1/alerts/{identifier}/cases", self.analyst, "POST")
        self.assertEqual(status, 200)
        path = f"/v1/cases/{case['case_id']}/decisions"
        body = {"outcome": "uncertain", "reason": "[TEST AUTOMATIQUE SUR DONNÉES SYNTHÉTIQUES] Aucune décision bancaire humaine.", "origin": "automated_test"}
        headers = {"Idempotency-Key": str(uuid4())}
        status, first, _ = self.request(path, self.analyst, "POST", body, headers)
        self.assertEqual(status, 201)
        status, repeated, _ = self.request(path, self.analyst, "POST", body, headers)
        self.assertEqual(status, 200)
        self.assertEqual(first["decision_id"], repeated["decision_id"])
        self.assertEqual(first["version"], repeated["version"])
        self.assertEqual(first["origin"], "automated_test")
        self.assertEqual(self.request(path, self.analyst, "POST", body | {"outcome": "legitimate"}, headers)[0], 409)
        concurrent_headers = {"Idempotency-Key": str(uuid4())}
        with ThreadPoolExecutor(max_workers=4) as executor:
            replies = list(executor.map(lambda _: self.request(path, self.analyst, "POST", body, concurrent_headers), range(4)))
        self.assertEqual(sorted(x[0] for x in replies), [200, 200, 200, 201])
        self.assertEqual(len({x[1]["decision_id"] for x in replies}), 1)

    def test_z_quota_is_enforced(self):
        statuses = []
        for _ in range(65):
            status, body, headers = self.request("/v1/alerts?limit=1", self.reader)
            statuses.append(status)
            if status == 429:
                self.assertTrue(1 <= int(headers["Retry-After"]) <= 60)
                break
        self.assertIn(429, statuses)


if __name__ == "__main__":
    unittest.main()
