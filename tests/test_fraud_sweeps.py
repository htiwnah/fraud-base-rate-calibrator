"""Threshold and base-rate sensitivity tests for fraud-base-rate-calibrator."""

from __future__ import annotations

import unittest
from pathlib import Path

from fraud_base_rate_calibrator.calibrator import calibrate_alerts, load_transactions
from fraud_base_rate_calibrator.config import FraudPolicy

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "fraud_scores.jsonl"


class TestThresholdSweepProperties(unittest.TestCase):
    def test_raising_threshold_to_point_eight_eliminates_false_positives(self) -> None:
        s = calibrate_alerts(load_transactions(FIX), FraudPolicy(score_threshold=0.80))
        self.assertEqual(s.false_positives, 0)
        self.assertEqual(s.precision, 1.0)
        self.assertTrue(s.gate_passed)

    def test_lowering_threshold_to_point_six_recovers_all_fraud_with_six_fps(self) -> None:
        s = calibrate_alerts(load_transactions(FIX), FraudPolicy(score_threshold=0.60))
        self.assertEqual(s.recall, 1.0)
        self.assertEqual(s.false_positives, 6)

    def test_confusion_counts_sum_to_total_transactions_at_every_threshold(self) -> None:
        items = load_transactions(FIX)
        for th in (0.20, 0.50, 0.70, 0.85, 0.95):
            s = calibrate_alerts(items, FraudPolicy(score_threshold=th))
            tot = s.true_positives + s.false_positives + s.false_negatives + s.true_negatives
            self.assertEqual(tot, s.total_transactions)

    def test_to_dict_contains_all_fifty_verdicts(self) -> None:
        d = calibrate_alerts(load_transactions(FIX), FraudPolicy()).to_dict()
        self.assertEqual(len(d["verdicts"]), 50)  # type: ignore[arg-type]

    def test_deterministic_across_repeated_runs(self) -> None:
        items = load_transactions(FIX)
        pol = FraudPolicy()
        self.assertEqual(calibrate_alerts(items, pol).to_dict(), calibrate_alerts(items, pol).to_dict())
