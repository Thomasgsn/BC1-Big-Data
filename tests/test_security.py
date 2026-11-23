"""Contrat TLS : configurations artificielles, aucune identité privée réelle."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rncp_bc1.security import kafka_stream_options,jdbc_sql_url,mongo_spark_uri,mongo_tls_options,sql_tls_options

VALID='''security.protocol=SSL
ssl.keystore.type=PKCS12
ssl.keystore.location=/identity/identity.p12
ssl.keystore.password=synthetic-fixture-password
ssl.key.password=synthetic-fixture-password
ssl.truststore.type=PKCS12
ssl.truststore.location=/identity/trust.p12
ssl.truststore.password=synthetic-fixture-password
ssl.endpoint.identification.algorithm=https
'''

class TransportSecurityTest(unittest.TestCase):
    def read(self,text):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'client.properties';p.write_text(text)
            with patch.dict(os.environ,{'BC1_KAFKA_TLS_PROPERTIES':str(p)}):
                return kafka_stream_options()

    def test_tls_options_preserve_complete_explicit_contract(self):
        result=self.read(VALID)
        self.assertEqual(result['kafka.security.protocol'],'SSL')
        self.assertEqual(result['kafka.ssl.endpoint.identification.algorithm'],'https')
        self.assertEqual(len(result),9)

    def test_refuses_disabled_hostname_plaintext_duplicate_and_unknown(self):
        for text in [VALID.replace('https',''),VALID.replace('security.protocol=SSL','security.protocol=PLAINTEXT'),VALID+'security.protocol=SSL\n',VALID+'sasl.jaas.config=untrusted\n',VALID.replace('ssl.truststore.password=synthetic-fixture-password\n','')]:
            with self.subTest(configuration=text),self.assertRaises(ValueError):self.read(text)

    def test_missing_file_and_size_limit_fail_instead_of_plaintext_fallback(self):
        with patch.dict(os.environ,{'BC1_KAFKA_TLS_PROPERTIES':'/nonexistent/explicit-tls-config'}):
            with self.assertRaises(FileNotFoundError):kafka_stream_options()
        with self.assertRaises(ValueError):self.read('#' * 16385)

    def test_database_tls_validates_ca_and_hostname(self):
        with patch.dict(os.environ,{'BC1_DB_TLS_CA':'/public-ca/ca.crt'}):
            self.assertEqual(sql_tls_options(),{'sslmode':'verify-full','sslrootcert':'/public-ca/ca.crt'})
            self.assertEqual(mongo_tls_options(),{'tls':True,'tlsCAFile':'/public-ca/ca.crt'})
            self.assertIn('sslmode=verify-full',jdbc_sql_url())
            self.assertTrue(mongo_spark_uri('synthetic:password@fixture').endswith('&tls=true'))
            self.assertIn('synthetic%3Apassword%40fixture',mongo_spark_uri('synthetic:password@fixture'))

if __name__=='__main__':unittest.main()
