"""Explicit policy loader for fraud alert thresholds and false-positive budgets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FraudPolicy:
    """Immutable operating threshold and false-positive alert budget."""

    policy_version: str = "1.0"
    score_threshold: float = 0.70
    max_allowed_false_positives: int = 0
    fixture_path: str = "fixtures/fraud_scores.jsonl"

    def validate(self) -> None:
        """Enforce valid score threshold and non-negative FP budget."""
        if not (0.0 <= self.score_threshold <= 1.0):
            raise ValueError("score_threshold must lie in [0.0, 1.0]")
        if self.max_allowed_false_positives < 0:
            raise ValueError("max_allowed_false_positives must be >= 0")


def load_policy(path: str | Path | None = None) -> FraudPolicy:
    """Load FraudPolicy from JSON or return validated defaults."""
    if path is None:
        cfg = FraudPolicy()
        cfg.validate()
        return cfg
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Policy not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Policy must be a JSON object")
    cfg = FraudPolicy(**raw)
    cfg.validate()
    return cfg
