"""Fixtures binaires/SCRAM artificielles, sans réseau ni vrai secret ; client corrigé uniquement."""

import base64
import json
import struct
import time
import tracemalloc
import unittest

import kafka
from kafka.errors import InvalidReceiveError
from kafka.protocol.parser import KafkaProtocol
from kafka.sasl.scram import ScramClient


class KafkaSecurityRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ne jamais déclencher ces tailles/itérations sur la version vulnérable.
        if kafka.__version__ != "2.3.2":
            raise RuntimeError("Ce contrôle adversarial est réservé au wheel 2.3.2 vérifié")

    def test_protocol_rejects_invalid_size_before_allocation(self):
        for length in [-1, 100000001, 2147483647]:
            with self.subTest(length=length):
                parser = KafkaProtocol()
                tracemalloc.start()
                try:
                    with self.assertRaises(InvalidReceiveError):
                        parser.receive_bytes(struct.pack(">i", length))
                    _, peak = tracemalloc.get_traced_memory()
                    self.assertLess(peak, 1024*1024)
                finally:
                    tracemalloc.stop()
        # Trame partielle de taille valide : ne pas tout rejeter pour faire passer le test.
        self.assertEqual(KafkaProtocol().receive_bytes(struct.pack(">i", 8)+b"\x00\x00"), [])

    def test_scram_rejects_unbounded_iterations_before_derivation(self):
        def message(client, iterations):
            return b"r="+client.nonce+b"SERVER_FIXTURE,s="+base64.b64encode(b"TEST_SALT")+b",i="+iterations
        for value in [b"2147483647", b"1000001", b"not-an-integer"]:
            with self.subTest(iterations=value):
                client = ScramClient("TEST_USER", "TEST_ONLY_SECRET", "SCRAM-SHA-256")
                client.first_message()
                with self.assertRaises(ValueError):
                    client.process_server_first_message(message(client, value))
                self.assertIsNone(client.salted_password)
        client = ScramClient("TEST_USER", "TEST_ONLY_SECRET", "SCRAM-SHA-256")
        client.first_message()
        client.process_server_first_message(message(client, b"4096"))
        self.assertEqual(len(client.salted_password), 32)


if __name__ == "__main__":
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(KafkaSecurityRegression))
    print(json.dumps({"event": "kafka_client_security_regression", "client_version": kafka.__version__,
                      "tests": result.testsRun, "success": result.wasSuccessful(), "seconds": time.monotonic()-started,
                      "fixture": "synthetic parser/SCRAM messages, no network, no real credentials"}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
