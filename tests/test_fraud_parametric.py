"""Parametric verification across all 50 scored transactions."""

from __future__ import annotations

import unittest
from pathlib import Path
from fraud_base_rate_calibrator.calibrator import calibrate_alerts, load_transactions
from fraud_base_rate_calibrator.config import FraudPolicy

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "fraud_scores.jsonl"
_ITEMS = load_transactions(FIX)
_FULL = calibrate_alerts(_ITEMS, FraudPolicy())


class TestPerTxProperties(unittest.TestCase):
    pass


def _bind(idx: int) -> None:
    v = _FULL.verdicts[idx]

    def _t(self: unittest.TestCase) -> None:
        self.assertIn(v.label, {'TP', 'FP', 'FN', 'TN'})
        self.assertEqual(v.predicted_alert, v.risk_score >= 0.70)

    setattr(TestPerTxProperties, f"test_tx_{v.tx_id.lower()}", _t)


for _i in range(len(_ITEMS)):
    _bind(_i)
