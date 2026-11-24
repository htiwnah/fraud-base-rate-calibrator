"""Property, boundary, and CLI tests for fraud-base-rate-calibrator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fraud_base_rate_calibrator.calibrator import (
    TxScore,
    calibrate_alerts,
    compute_roc_auc,
    load_transactions,
)
from fraud_base_rate_calibrator.cli import main as cli_main, render_table
from fraud_base_rate_calibrator.config import FraudPolicy, load_policy

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "fraud_scores.jsonl"
POL = ROOT / "policy" / "fraud_policy.json"


class TestFraudProperties(unittest.TestCase):
    def test_default_and_committed_policies_validate(self) -> None:
        FraudPolicy().validate()
        self.assertAlmostEqual(load_policy(POL).score_threshold, 0.70)
        self.assertEqual(load_policy(None).max_allowed_false_positives, 0)

    def test_invalid_policy_boundaries_rejected(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_policy(Path("/tmp/missing_fpol_999.json"))
        with self.assertRaises(ValueError):
            FraudPolicy(score_threshold=1.5).validate()
        with self.assertRaises(ValueError):
            FraudPolicy(max_allowed_false_positives=-1).validate()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "p.json"
            p.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_policy(p)

    def test_loader_rejects_missing_empty_bad_line_and_out_of_range_score(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_transactions(Path("/tmp/missing_ffix_999.jsonl"))
        with tempfile.TemporaryDirectory() as tmp:
            e = Path(tmp) / "e.jsonl"
            e.write_text("\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_transactions(e)
            b = Path(tmp) / "b.jsonl"
            b.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_transactions(b)
            o = Path(tmp) / "o.jsonl"
            o.write_text(
                json.dumps({"tx_id": "T1", "channel": "c", "is_fraud": False, "risk_score": 1.4})
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_transactions(o)

    def test_war_story_null_risk_score_coerced_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "n.jsonl"
            row = {"tx_id": "TN", "channel": "upi", "is_fraud": False, "risk_score": None}
            p.write_text(json.dumps(row) + "\n", encoding="utf-8")
            s = calibrate_alerts(load_transactions(p), FraudPolicy())
            self.assertEqual(s.true_negatives, 1)

    def test_committed_fixture_shows_high_roc_auc_yet_low_precision_due_to_base_rate(self) -> None:
        s = calibrate_alerts(load_transactions(FIX), load_policy(POL))
        self.assertEqual(s.total_transactions, 50)
        self.assertAlmostEqual(s.base_rate_pct, 8.0)
        self.assertGreater(s.roc_auc, 0.90)
        self.assertEqual(s.false_positives, 6)
        self.assertEqual(s.true_positives, 3)
        self.assertAlmostEqual(s.precision, 0.3333)
        self.assertAlmostEqual(s.f1_score, 0.4615)
        self.assertFalse(s.gate_passed)

    def test_empty_items_and_single_class_roc_auc_edge_cases(self) -> None:
        with self.assertRaises(ValueError):
            calibrate_alerts([], FraudPolicy())
        self.assertEqual(compute_roc_auc([TxScore("T1", "c", False, 0.5)]), 0.0)
        self.assertAlmostEqual(
            compute_roc_auc([TxScore("T1", "c", True, 0.5), TxScore("T2", "c", False, 0.5)]),
            0.5,
        )

    def test_cli_exit_codes_and_table_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            oj = Path(tmp) / "o.json"
            self.assertEqual(
                cli_main(["calibrate", "--fixture", str(FIX), "--policy", str(POL), "--out", str(oj)]),
                1,
            )
            pf = Path(tmp) / "p.json"
            pf.write_text(json.dumps({"max_allowed_false_positives": 50}), encoding="utf-8")
            rc = cli_main([
                "calibrate", "--fixture", str(FIX), "--policy", str(pf),
                "--out", str(oj), "--json-only",
            ])
            self.assertEqual(rc, 0)
        self.assertEqual(cli_main(["calibrate", "--fixture", "/tmp/missing_f_888.jsonl"]), 2)
        self.assertEqual(cli_main(["calibrate", "--max-rows", "abc"]), 2)
        self.assertEqual(cli_main(["--help"]), 0)
        s = calibrate_alerts(load_transactions(FIX), load_policy(POL))
        self.assertIn("TX004", render_table(s, max_rows=5))
