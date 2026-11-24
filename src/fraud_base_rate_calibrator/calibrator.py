"""Deterministic precision, recall, F1, ROC-AUC, and base-rate alert calibrator."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from fraud_base_rate_calibrator.config import FraudPolicy


@dataclass(frozen=True)
class TxScore:
    """Single scored transaction."""

    tx_id: str
    channel: str
    is_fraud: bool
    risk_score: float


@dataclass(frozen=True)
class AlertVerdict:
    """Per-transaction confusion classification."""

    tx_id: str
    channel: str
    is_fraud: bool
    risk_score: float
    predicted_alert: bool
    label: str


@dataclass(frozen=True)
class FraudSummary:
    """Aggregated calibration report exposing ROC-AUC vs low-base-rate precision."""

    total_transactions: int
    actual_fraud_count: int
    base_rate_pct: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    roc_auc: float
    precision: float
    recall: float
    f1_score: float
    resolution_floor_pct: float
    gate_passed: bool
    verdicts: list[AlertVerdict] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize summary to a plain JSON dictionary."""
        return {
            "total_transactions": self.total_transactions,
            "actual_fraud_count": self.actual_fraud_count,
            "base_rate_pct": self.base_rate_pct,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "roc_auc": self.roc_auc,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "resolution_floor_pct": self.resolution_floor_pct,
            "gate_passed": self.gate_passed,
            "verdicts": [
                {
                    "tx_id": v.tx_id,
                    "channel": v.channel,
                    "is_fraud": v.is_fraud,
                    "risk_score": v.risk_score,
                    "predicted_alert": v.predicted_alert,
                    "label": v.label,
                }
                for v in self.verdicts
            ],
        }


def compute_roc_auc(items: list[TxScore]) -> float:
    """Exact pairwise Mann-Whitney ROC-AUC computation in stdlib."""
    pos = [x.risk_score for x in items if x.is_fraud]
    neg = [x.risk_score for x in items if not x.is_fraud]
    if not pos or not neg:
        return 0.0
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return round(wins / (len(pos) * len(neg)), 4)


def load_transactions(path: str | Path) -> list[TxScore]:
    """Load JSONL scored transactions with explicit range validation."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fraud fixture not found: {p}")
    out: list[TxScore] = []
    for ln_no, raw_ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = raw_ln.strip()
        if not s:
            continue
        r = json.loads(s)
        if not isinstance(r, dict):
            raise ValueError(f"Line {ln_no} must be a JSON object")
        sc = 0.0 if r.get("risk_score") is None else float(r["risk_score"])
        if not (0.0 <= sc <= 1.0):
            raise ValueError(f"risk_score out of range on line {ln_no}")
        out.append(TxScore(str(r["tx_id"]), str(r["channel"]), bool(r["is_fraud"]), sc))
    if not out:
        raise ValueError(f"No transactions in {p}")
    return out


def calibrate_alerts(items: list[TxScore], policy: FraudPolicy) -> FraudSummary:
    """Evaluate ROC-AUC, confusion counts, precision, recall, and F1."""
    if not items:
        raise ValueError("Cannot calibrate empty transaction list")
    policy.validate()
    tp = fp = fn = tn = fraud = 0
    verdicts: list[AlertVerdict] = []
    for it in items:
        fraud += int(it.is_fraud)
        pred = it.risk_score >= policy.score_threshold
        if pred and it.is_fraud:
            tp += 1
            lbl = "TP"
        elif pred and not it.is_fraud:
            fp += 1
            lbl = "FP"
        elif not pred and it.is_fraud:
            fn += 1
            lbl = "FN"
        else:
            tn += 1
            lbl = "TN"
        verdicts.append(AlertVerdict(it.tx_id, it.channel, it.is_fraud, it.risk_score, pred, lbl))
    tot = len(verdicts)
    prec = round(tp / (tp + fp), 4) if (tp + fp) else 0.0
    rec = round(tp / (tp + fn), 4) if (tp + fn) else 0.0
    f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) else 0.0
    return FraudSummary(
        total_transactions=tot,
        actual_fraud_count=fraud,
        base_rate_pct=round((fraud / tot) * 100.0, 2),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        roc_auc=compute_roc_auc(items),
        precision=prec,
        recall=rec,
        f1_score=f1,
        resolution_floor_pct=round((1.0 / tot) * 100.0, 2),
        gate_passed=fp <= policy.max_allowed_false_positives,
        verdicts=verdicts,
    )
