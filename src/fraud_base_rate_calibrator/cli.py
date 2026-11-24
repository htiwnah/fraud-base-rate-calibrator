"""CLI for fraud-base-rate-calibrator with explicit 0/1/2 exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fraud_base_rate_calibrator.calibrator import FraudSummary, calibrate_alerts, load_transactions
from fraud_base_rate_calibrator.config import load_policy


def render_table(s: FraudSummary, max_rows: int = 12) -> str:
    """Render scannable fraud alert table contrasting ROC-AUC against precision."""
    hdr = f"{'TxID':<7} {'Channel':<15} {'Fraud':<5} {'Score':>6} {'Alert':<5} {'Label'}"
    lines = [
        "Fraud Base-Rate Calibrator: ROC-AUC vs Operating Alert Precision",
        (
            f"Tx: {s.total_transactions} | Base Rate: {s.base_rate_pct:.2f}% | "
            f"ROC-AUC: {s.roc_auc:.4f} | FP: {s.false_positives} | TP: {s.true_positives}"
        ),
        f"Precision: {s.precision:.4f} | Recall: {s.recall:.4f} | F1: {s.f1_score:.4f}",
        hdr,
        "-" * len(hdr),
    ]
    ordered = sorted(
        s.verdicts,
        key=lambda v: (0 if v.label == "FP" else (1 if v.label == "FN" else 2), v.tx_id),
    )
    for v in ordered[:max_rows]:
        lines.append(
            f"{v.tx_id:<7} {v.channel:<15} {str(v.is_fraud):<5} "
            f"{v.risk_score:>6.3f} {str(v.predicted_alert):<5} {v.label}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Execute CLI and return 0 (pass), 1 (answered no), or 2 (input error)."""
    p = argparse.ArgumentParser(prog="fraud-calibrator")
    sub = p.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("calibrate")
    cp.add_argument("--fixture", default="fixtures/fraud_scores.jsonl")
    cp.add_argument("--policy", default=None)
    cp.add_argument("--out", default="reports/fraud_audit.json")
    cp.add_argument("--max-rows", type=int, default=12)
    cp.add_argument("--json-only", action="store_true")
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        pol = load_policy(args.policy)
        s = calibrate_alerts(load_transactions(args.fixture), pol)
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(s.to_dict(), indent=2) + "\n", encoding="utf-8")
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        sys.stderr.write(f"Calibration input error: {exc}\n")
        return 2
    if args.json_only:
        sys.stdout.write(json.dumps(s.to_dict(), indent=2) + "\n")
    else:
        sys.stdout.write(render_table(s, max_rows=args.max_rows) + "\n")
    return 0 if s.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
