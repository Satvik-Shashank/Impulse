"""Runtime configuration loaded from environment variables."""

import os


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None or not value.strip() else float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None or not value.strip() else int(value)


AUTO_RESPOND_CONFIDENCE = _env_float("AUTO_RESPOND_CONFIDENCE", 0.70)
COST_FP = _env_int("COST_FP", 1000)
COST_FN = _env_int("COST_FN", 350)
SAVINGS_TP = _env_int("SAVINGS_TP", 2250)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
