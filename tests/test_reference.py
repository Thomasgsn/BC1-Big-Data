"""Oracle CSV indépendant de Spark ; fixtures synthétiques."""

import csv
from pathlib import Path
import tempfile
import unittest

from rncp_bc1.dataset import HEADERS
from rncp_bc1.jobs.verify import expected


class ReferenceTest(unittest.TestCase):
    def test_decimal_totals_and_selected_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"synthetic.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=HEADERS)
                writer.writeheader()
                for amount, kind in [("0.10", "PAYMENT"), ("0.20", "PAYMENT"), ("900", "TRANSFER")]:
                    writer.writerow({"amount": amount, "type": kind})
            self.assertEqual(expected(path, 2), {"PAYMENT": {"count": 2, "amount": "0.30"}})
            with self.assertRaises(ValueError):
                expected(path, 4)


if __name__ == "__main__":
    unittest.main()
