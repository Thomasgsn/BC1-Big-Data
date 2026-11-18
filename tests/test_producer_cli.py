"""CLI réelle en mode fichier, avec données de test artificielles déclarées."""

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rncp_bc1.dataset import HEADERS


class ProducerCliTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root/"synthetic.csv"
        self.output = self.root/"events.jsonl"
        self.row = ["1", "TRANSFER", "1.00", "C1", "2", "1", "C2", "0", "1", "1", "0"]
        self.write_csv(self.row)

    def write_csv(self, row):
        with self.source.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(HEADERS)
            writer.writerow(row)

    def command(self, *extra):
        env = os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[1]/"src")}
        return subprocess.run([sys.executable, "-m", "rncp_bc1.producer", "--csv", str(self.source),
                               "--sha256", hashlib.sha256(self.source.read_bytes()).hexdigest(),
                               "--run-id", "synthetic-cli", "--rate", "100000", "--jsonl", str(self.output), *extra],
                              capture_output=True, text=True, timeout=10, env=env)

    def test_publishes_only_complete_jsonl(self):
        result = self.command("--limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text())["source_row"], 1)
        self.assertEqual(json.loads(result.stderr)["mode"], "jsonl_control")

    def test_invalid_row_never_publishes_partial_output(self):
        self.row[3] = ""
        self.write_csv(self.row)
        result = self.command()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(sorted(x.name for x in self.root.iterdir()), ["synthetic.csv"])

    def test_existing_output_is_preserved(self):
        self.output.write_text("keep-me")
        self.assertEqual(self.command().returncode, 1)
        self.assertEqual(self.output.read_text(), "keep-me")

    def test_checksum_mismatch_is_explicit(self):
        result = self.command("--sha256", "0"*64)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Empreinte", result.stderr)
        self.assertFalse(self.output.exists())

    def test_invalid_rate_and_empty_selection_are_errors(self):
        for extra in [("--rate", "nan"), ("--rate", "0"), ("--start-row", "2")]:
            with self.subTest(extra=extra):
                self.assertEqual(self.command(*extra).returncode, 1)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
