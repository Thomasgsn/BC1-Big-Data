"""Tests de contrat avec transactions synthétiques explicitement étiquetées."""

import csv
from pathlib import Path
import tempfile
import unittest

from rncp_bc1.dataset import HEADERS
from rncp_bc1.producer import events, selected_destination, selected_source_row
from rncp_bc1.transactions import ReplayContext, envelope, money, predictive_values


class TransactionTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(zip(HEADERS, ["2", "TRANSFER", "100.01", "C1", "200", "99.99", "C2", "0", "100.01", "1", "0"]))
        self.context = ReplayContext("a" * 64, "synthetic-test")

    def test_identity_independent_of_replay_and_time(self):
        one = envelope(self.row, 1, self.context, "2026-01-01T00:00:00Z")
        two = envelope(self.row, 1, ReplayContext("a"*64, "another-run"), "2026-01-02T00:00:00Z")
        self.assertEqual(one["transaction_id"], two["transaction_id"])
        self.assertNotEqual(one["transaction_id"], envelope(self.row, 2, self.context)["transaction_id"])
        self.assertEqual(one["event_time"], "2000-01-01T01:00:00+00:00")
        self.assertIs(one["event_time_synthetic"], True)
        self.assertEqual(one["payload"]["amount"], "100.01")

    def test_money_never_silently_rounds(self):
        self.assertEqual(money("0"), "0.00")
        self.assertEqual(money("100.010"), "100.01")
        for value in ["-1", "NaN", "Infinity", "0.001", "10000000000000000", "oops"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)

    def test_rejects_invalid_context_and_time(self):
        for sha, run, epoch in [("bad", "run", "2000-01-01T00:00:00Z"), ("a"*64, "../escape", "2000-01-01T00:00:00Z"),
                                ("a"*64, "run", "2000-01-01T00:00:00"), ("a"*64, "run", "2000-01-01T00:00:00+02:00")]:
            with self.subTest(run=run, epoch=epoch), self.assertRaises(ValueError):
                ReplayContext(sha, run, epoch)

    def test_invalid_payload_and_account_ids(self):
        for change in [{"step": "0"}, {"step": "1.2"}, {"type": "UNKNOWN"}, {"nameOrig": ""},
                       {"nameDest": "../path"}, {"isFraud": "2"}, {"amount": "-2"}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                envelope(self.row | change, 1, self.context)

    def test_predictive_feature_allowlist_excludes_all_balances_and_labels(self):
        values = predictive_values(envelope(self.row, 1, self.context)["payload"])
        self.assertEqual(set(values), {"step", "type", "amount"})

    def test_selects_source_positions_without_renumbering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"synthetic.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows([self.row]*3)
            selected = list(events(path, self.context, start_row=2, limit=1))
            self.assertEqual([x["source_row"] for x in selected], [2])
            with self.assertRaises(ValueError):
                list(events(path, self.context, start_row=4))

    def test_sampling_is_deterministic_and_preserves_source_identity(self):
        one = [n for n in range(1, 1001) if selected_source_row("a"*64, n, 8, 42)]
        two = [n for n in range(1, 1001) if selected_source_row("a"*64, n, 8, 42)]
        other = [n for n in range(1, 1001) if selected_source_row("a"*64, n, 8, 43)]
        self.assertEqual(one, two)
        self.assertNotEqual(one, other)
        self.assertTrue(0 < len(one) < 1000)
        self.assertTrue(all(selected_source_row("a"*64, n) for n in range(1, 100)))
        with self.assertRaises(ValueError):
            selected_source_row("a"*64, 1, 0)

    def test_destination_sampling_keeps_whole_account_history(self):
        accounts = [f"C{n}" for n in range(1000)]
        kept = [a for a in accounts if selected_destination("a"*64, a, 8, 42)]
        self.assertEqual(kept, [a for a in accounts if selected_destination("a"*64, a, 8, 42)])
        self.assertNotEqual(kept, [a for a in accounts if selected_destination("a"*64, a, 8, 43)])
        self.assertTrue(0 < len(kept) < 1000)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            rows = [{**self.row, "nameDest": kept[0]}, {**self.row, "nameDest": kept[0]},
                    {**self.row, "nameDest": next(a for a in accounts if a not in kept)}]
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)
            selected = list(events(path, self.context, sample_modulus=8, sample_key="destination"))
            self.assertEqual([x["source_row"] for x in selected], [1, 2])
            with self.assertRaises(ValueError):
                list(events(path, self.context, sample_key="inconnu"))


if __name__ == "__main__":
    unittest.main()
