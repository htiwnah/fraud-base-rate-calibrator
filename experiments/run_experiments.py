"""Deterministic FinOps/Fraud threshold calibration experiments."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fraud_base_rate_calibrator.calibrator import calibrate_alerts, load_transactions  # noqa: E402
from fraud_base_rate_calibrator.config import FraudPolicy, load_policy  # noqa: E402


def run_all_experiments(repo_root: Path | None = None) -> dict[str, object]:
    """Run four deterministic fraud base-rate calibration experiments."""
    root = repo_root or ROOT_DIR
    out_dir = root / "docs" / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)
    pol = load_policy(root / "policy" / "fraud_policy.json")
    items = load_transactions(root / "fixtures" / "fraud_scores.jsonl")
    full = calibrate_alerts(items, pol)

    exp1 = {
        "total_transactions": full.total_transactions,
        "actual_fraud_count": full.actual_fraud_count,
        "base_rate_pct": full.base_rate_pct,
        "roc_auc": full.roc_auc,
        "true_positives": full.true_positives,
        "false_positives": full.false_positives,
        "false_negatives": full.false_negatives,
        "precision": full.precision,
        "recall": full.recall,
        "f1_score": full.f1_score,
        "resolution_floor_pct": full.resolution_floor_pct,
    }
    (out_dir / "exp1_base_rate.json").write_text(json.dumps(exp1, indent=2) + "\n", encoding="utf-8")

    exp2 = {
        "rows": [
            {
                "threshold": th,
                "fp": calibrate_alerts(items, FraudPolicy(score_threshold=th)).false_positives,
                "precision": calibrate_alerts(items, FraudPolicy(score_threshold=th)).precision,
                "recall": calibrate_alerts(items, FraudPolicy(score_threshold=th)).recall,
                "f1": calibrate_alerts(items, FraudPolicy(score_threshold=th)).f1_score,
            }
            for th in (0.60, 0.70, 0.80)
        ]
    }
    (out_dir / "exp2_threshold_sweep.json").write_text(
        json.dumps(exp2, indent=2) + "\n", encoding="utf-8"
    )
    return {"exp1": exp1, "exp2": exp2}


def main() -> None:
    e1 = run_all_experiments()["exp1"]
    print(
        f"Exp1 | tx={e1['total_transactions']} | roc_auc={e1['roc_auc']} | "
        f"fp={e1['false_positives']} | precision={e1['precision']} | f1={e1['f1_score']}"
    )


if __name__ == "__main__":
    main()
