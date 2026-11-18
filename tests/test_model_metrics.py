"""Effectifs artificiels de contrôle ; aucun résultat ML PaySim inventé."""

import unittest
from rncp_bc1.model_metrics import confusion_metrics, select_threshold


class ModelMetricsTest(unittest.TestCase):
    def test_imbalanced_baseline_exposes_zero_recall(self):
        result = confusion_metrics(0, 0, 999, 1)
        self.assertEqual(result["accuracy"], 0.999)
        self.assertEqual(result["recall"], 0)
        self.assertEqual(result["f2"], 0)

    def test_precision_recall_and_confusion_counts(self):
        result = confusion_metrics(8, 2, 88, 2)
        self.assertEqual(result["precision"], 0.8)
        self.assertEqual(result["recall"], 0.8)
        self.assertAlmostEqual(result["false_positive_rate"], 2/90)
        self.assertEqual(result["f2"], 0.8)

    def test_undefined_recall_does_not_become_perfect_score(self):
        result = confusion_metrics(0, 0, 100, 0)
        self.assertIsNone(result["recall"])
        with self.assertRaises(ValueError):
            select_threshold([{**result, "threshold": 0.5}])

    def test_rejects_empty_and_negative_counts(self):
        for values in [(0, 0, 0, 0), (-1, 0, 1, 1), (1.5, 0, 1, 0)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                confusion_metrics(*values)

    def test_threshold_selection_uses_validation_f2(self):
        candidates = [{"threshold": 0.5, **confusion_metrics(5, 0, 100, 5)},
                      {"threshold": 0.2, **confusion_metrics(9, 2, 98, 1)}]
        self.assertEqual(select_threshold(candidates)["threshold"], 0.2)


if __name__ == "__main__":
    unittest.main()
