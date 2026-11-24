"""Contrat du jeu de variables ; le calcul Spark est vérifié dans le conteneur driver."""

import unittest

from rncp_bc1.jobs.account_features import BASELINE_FEATURES, DESTINATION_FEATURES, features_for
from rncp_bc1.jobs.train import THRESHOLDS, step_quantiles


class AccountFeaturesTest(unittest.TestCase):
    def test_feature_sets_never_include_accounts_labels_or_balances(self):
        self.assertEqual(features_for("baseline"), BASELINE_FEATURES)
        self.assertEqual(features_for("destination_history"), BASELINE_FEATURES + DESTINATION_FEATURES)
        forbidden = {"target", "source", "isFraud", "isFlaggedFraud", "oldbalanceOrg", "newbalanceOrig",
                     "oldbalanceDest", "newbalanceDest"}
        self.assertFalse(forbidden & set(features_for("destination_history")))
        with self.assertRaises(ValueError):
            features_for("inconnu")


    def test_step_quantiles_follow_cumulative_row_counts(self):
        counts = [(3, 10), (1, 50), (2, 30), (4, 10)]
        self.assertEqual(step_quantiles(counts, [0.6, 0.8]), [2, 2])
        self.assertEqual(step_quantiles(counts, [0.5, 0.95]), [1, 4])
        with self.assertRaises(ValueError):
            step_quantiles([], [0.5])

    def test_threshold_grid_goes_beyond_previous_edge(self):
        self.assertEqual(list(THRESHOLDS), sorted(set(THRESHOLDS)))
        self.assertGreater(max(THRESHOLDS), 0.9)
        self.assertTrue(all(0 < value < 1 for value in THRESHOLDS))


if __name__ == "__main__":
    unittest.main()
