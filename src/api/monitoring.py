"""Model monitoring: prediction logging and drift detection.

Writes every pipeline prediction to a JSONL log file and computes
rolling statistics to detect distribution shifts in incoming disputes.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LOG_PATH = os.path.join(_PROJECT_ROOT, "results", "monitoring_log.jsonl")
DEFAULT_BASELINE_PATH = os.path.join(_PROJECT_ROOT, "results", "monitoring_baseline.json")


def population_stability_index(expected, actual, bins=10):
    """Calculate PSI using quantile bins from the expected population."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) == 0 or len(actual) == 0:
        return None
    breakpoints = np.unique(np.percentile(expected, np.linspace(0, 100, bins + 1)))
    if len(breakpoints) < 2:
        breakpoints = np.array([breakpoints[0] - 1e-6, breakpoints[0] + 1e-6])
    else:
        breakpoints = np.concatenate(([-np.inf], breakpoints[1:-1], [np.inf]))
    expected_pct = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_pct = np.histogram(actual, breakpoints)[0] / len(actual)
    expected_pct = np.clip(expected_pct, 1e-6, None)
    actual_pct = np.clip(actual_pct, 1e-6, None)
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


class MonitoringLog:
    """Append-only JSONL prediction log with drift analysis."""

    def __init__(self, log_path: str = DEFAULT_LOG_PATH, baseline_path: str = DEFAULT_BASELINE_PATH):
        self.log_path = log_path
        self.baseline_path = baseline_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_prediction(self, pipeline_result: dict) -> None:
        """Append a single prediction record to the monitoring log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "dispute_id": pipeline_result.get("dispute_id"),
            "reason_code": pipeline_result.get("classification", {}).get("predicted_reason_code"),
            "confidence": pipeline_result.get("classification", {}).get("confidence"),
            "evidence_strength": pipeline_result.get("evidence", {}).get("evidence_strength"),
            "win_probability": pipeline_result.get("win_probability"),
            "expected_value_inr": pipeline_result.get("expected_value_inr"),
            "action": pipeline_result.get("response", {}).get("action"),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_log(self, limit: Optional[int] = None) -> list:
        """Read the full log (or last `limit` entries)."""
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if limit:
            lines = lines[-limit:]
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def compute_drift_snapshot(self, window: int = 200) -> dict:
        """Compute rolling statistics over the last `window` predictions.

        Returns averages and distributions that can be compared against
        the training baseline to detect concept/data drift.
        """
        entries = self.read_log(limit=window)
        if not entries:
            return {
                "window_size": 0,
                "message": "No monitoring data available yet.",
            }

        n = len(entries)
        confidences = [e.get("confidence", 0) for e in entries if e.get("confidence") is not None]
        strengths = [e.get("evidence_strength", 0) for e in entries if e.get("evidence_strength") is not None]
        win_probs = [e.get("win_probability", 0) for e in entries if e.get("win_probability") is not None]
        baseline = None
        if os.path.exists(self.baseline_path):
            with open(self.baseline_path, "r", encoding="utf-8") as handle:
                baseline = json.load(handle)
        baseline_confidence = baseline_strength = []
        if baseline:
            baseline_confidence = baseline.get("confidence", [])
            baseline_strength = baseline.get("evidence_strength", [])

        # Reason code distribution
        rc_counts = {}
        action_counts = {"AUTO_SUBMIT": 0, "HUMAN_REVIEW": 0}
        for e in entries:
            rc = e.get("reason_code", "unknown")
            rc_counts[rc] = rc_counts.get(rc, 0) + 1
            action = e.get("action", "HUMAN_REVIEW")
            if action in action_counts:
                action_counts[action] += 1

        def _safe_avg(lst):
            return round(sum(lst) / len(lst), 4) if lst else 0.0

        def _safe_std(lst):
            if len(lst) < 2:
                return 0.0
            avg = sum(lst) / len(lst)
            var = sum((x - avg) ** 2 for x in lst) / (len(lst) - 1)
            return round(var ** 0.5, 4)

        return {
            "window_size": n,
            "time_range": {
                "earliest": entries[0].get("timestamp"),
                "latest": entries[-1].get("timestamp"),
            },
            "confidence": {
                "mean": _safe_avg(confidences),
                "std": _safe_std(confidences),
                "min": round(min(confidences), 4) if confidences else 0,
                "max": round(max(confidences), 4) if confidences else 0,
            },
            "evidence_strength": {
                "mean": _safe_avg(strengths),
                "std": _safe_std(strengths),
                "min": round(min(strengths), 4) if strengths else 0,
                "max": round(max(strengths), 4) if strengths else 0,
            },
            "win_probability": {
                "mean": _safe_avg(win_probs),
                "std": _safe_std(win_probs),
            },
            "reason_code_distribution": rc_counts,
            "action_distribution": action_counts,
            "auto_rate_pct": round(
                action_counts["AUTO_SUBMIT"] / n * 100, 1
            ) if n else 0.0,
            "psi": {
                "confidence": population_stability_index(baseline_confidence, confidences),
                "evidence_strength": population_stability_index(baseline_strength, strengths),
                "interpretation": "<0.10 stable; 0.10-0.25 moderate shift; >0.25 significant shift",
            },
            "recent_series": [
                {
                    "dispute_id": e.get("dispute_id", f"DSP-{i+1}"),
                    "confidence": round(float(e.get("confidence", 0)), 3),
                    "evidence_strength": round(float(e.get("evidence_strength", 0)), 3),
                    "win_probability": round(float(e.get("win_probability", 0)), 3),
                    "action": e.get("action", "HUMAN_REVIEW"),
                    "reason_code": str(e.get("reason_code", "")),
                }
                for i, e in enumerate(entries[-25:])
            ],
            "data_source": "runtime_prediction_log",
        }
