"""Fixtures synthétiques : tests de contrats, sans valeur statistique PaySim."""

import csv
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from rncp_bc1.dataset import CSV_NAME, HEADERS, prepare_archive, profile_csv, write_json


class DatasetTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def csv_file(self, rows, headers=HEADERS):
        path = self.root / "fixture-synthetic.csv"
        with path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerows(rows)
        return path

    def row(self, **changes):
        row = dict(zip(HEADERS, ["1", "TRANSFER", "100.01", "C_TEST_A", "200", "99.99",
                                 "C_TEST_B", "0", "100.01", "1", "0"]))
        row.update(changes)
        return [row[k] for k in HEADERS]

    def test_profile_counts_class_imbalance_and_decimal_precision(self):
        path = self.csv_file([self.row(), self.row(step="2", type="PAYMENT", isFraud="0", amount="0")])
        report = profile_csv(path)
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["invalid_rows"], 0)
        self.assertEqual(report["fraud_rate"], "0.5")
        self.assertEqual(report["amount_zero_rows"], 1)
        self.assertEqual(report["amount_max_decimal_places"], 2)
        self.assertEqual(report["numeric_ranges"]["amount"]["max"], "100.01")
        self.assertEqual(len(report["dataset"]["sha256"]), 64)
        self.assertEqual(report["step"]["fraud_by_step"], {1: 1})

    def test_reports_invalid_values_without_silent_coercion(self):
        path = self.csv_file([self.row(amount="NaN", isFraud="2", nameOrig="", step="1.5"),
                              self.row(amount="-1", type="UNKNOWN", oldbalanceDest="Infinity")])
        report = profile_csv(path)
        self.assertEqual(report["invalid_rows"], 2)
        self.assertEqual(report["missing_by_column"]["nameOrig"], 1)
        for key in ["invalid:amount", "invalid:isFraud", "invalid:step", "negative:amount", "invalid:type", "invalid:oldbalanceDest"]:
            self.assertEqual(report["errors"][key], 1)

    def test_missing_columns_and_extra_fields_are_errors(self):
        path = self.csv_file([self.row()[:-2], self.row() + ["extra"]])
        report = profile_csv(path)
        self.assertEqual(report["invalid_rows"], 2)
        self.assertEqual(report["errors"]["extra_columns"], 1)

    def test_step_order_is_measured(self):
        report = profile_csv(self.csv_file([self.row(step="2"), self.row(step="1")]))
        self.assertEqual(report["step"]["regressions"], 1)

    def test_rejects_wrong_header_and_empty_dataset(self):
        with self.assertRaises(ValueError):
            profile_csv(self.csv_file([], headers=["wrong"]))
        with self.assertRaises(ValueError):
            profile_csv(self.csv_file([]))

    def test_extraction_validates_member_and_preserves_existing_file(self):
        archive = self.root / "synthetic.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr(CSV_NAME, "synthetic fixture")
        result = prepare_archive(archive, self.root / "raw")
        self.assertEqual(result.read_text(), "synthetic fixture")
        with self.assertRaises(FileExistsError):
            prepare_archive(archive, self.root / "raw")
        self.assertEqual(result.read_text(), "synthetic fixture")

    def test_refuses_path_traversal_and_multiple_members(self):
        for members in [["../escape.csv"], [CSV_NAME, "other.csv"]]:
            with self.subTest(members=members):
                archive = self.root / "unsafe.zip"
                with zipfile.ZipFile(archive, "w") as zipped:
                    for member in members:
                        zipped.writestr(member, "synthetic fixture")
                with self.assertRaises(ValueError):
                    prepare_archive(archive, self.root / "raw")
        self.assertFalse((self.root / "escape.csv").exists())

    def test_failed_json_serialization_preserves_previous_report(self):
        path = self.root / "report.json"
        write_json(path, {"version": 1})
        with self.assertRaises(TypeError):
            write_json(path, {"unsupported": object()})
        self.assertEqual(json.loads(path.read_text()), {"version": 1})


if __name__ == "__main__":
    unittest.main()
