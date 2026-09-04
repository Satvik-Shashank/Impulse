"""Privacy-scoped parsing, mapping, validation, and staging for merchant uploads."""

import io
import json
import re
import threading
import time
import uuid
from typing import Any

import pandas as pd
from pydantic import ValidationError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 5000
SESSION_TTL_SECONDS = 3600

REQUIRED_FIELDS = {
    "dispute_amount", "days_to_dispute", "delivery_confirmed", "has_delivery_proof",
    "ip_geolocation_match", "avs_cvv_match", "customer_account_age_days",
    "customer_prior_disputes", "customer_prior_orders", "has_customer_correspondence",
    "has_3ds_authentication",
}
OPTIONAL_FIELDS = {
    "reason_code", "outcome", "product_category", "shipping_method", "card_network",
    "dispute_id", "currency", "transaction_date", "reason_code_label",
}
TARGET_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
FIELD_ALIASES = {
    "dispute_amount": ["amount", "txn amount", "transaction amount", "value", "order value"],
    "days_to_dispute": ["days to dispute", "days since order", "dispute lag", "time to dispute"],
    "delivery_confirmed": ["delivered", "delivery status", "delivery confirmed"],
    "has_delivery_proof": ["delivery proof", "proof of delivery", "pod"],
    "ip_geolocation_match": ["ip match", "ip geolocation", "location match"],
    "avs_cvv_match": ["avs cvv", "cvv match", "address verification"],
    "customer_account_age_days": ["account age", "customer age", "days as customer"],
    "customer_prior_disputes": ["prior disputes", "previous disputes"],
    "customer_prior_orders": ["prior orders", "previous orders", "order count"],
    "has_customer_correspondence": ["correspondence", "customer communication", "customer comms"],
    "has_3ds_authentication": ["3ds", "3-d secure", "three ds"],
    "card_network": ["card type", "card network", "network", "scheme"],
    "product_category": ["product category", "category", "product type"],
    "shipping_method": ["shipping", "delivery method", "fulfillment method"],
    "outcome": ["outcome", "result", "merchant outcome", "won or lost"],
    "reason_code": ["reason code", "chargeback code", "dispute code"],
}

_sessions: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _cleanup_sessions() -> None:
    cutoff = time.time() - SESSION_TTL_SECONDS
    with _lock:
        for session_id in list(_sessions):
            if _sessions[session_id]["created_at"] < cutoff:
                del _sessions[session_id]


def parse_content(filename: str, content: bytes, *, preview_only: bool = False) -> pd.DataFrame:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large. Maximum upload size is 10MB.")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        return pd.read_csv(io.BytesIO(content), nrows=MAX_ROWS)
    if suffix in {"xlsx", "xls"}:
        return pd.read_excel(io.BytesIO(content), nrows=MAX_ROWS)
    raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")


def suggest_column_mapping(columns: list[str]) -> dict[str, str]:
    mapping = {}
    normalized = {column: re.sub(r"[^a-z0-9 ]", "", str(column).lower()).strip() for column in columns}
    for field, aliases in FIELD_ALIASES.items():
        for column, name in normalized.items():
            if name == field or any(alias in name for alias in aliases):
                mapping[field] = column
                break
    return mapping


def validate_and_stage(df: pd.DataFrame, mapping: dict[str, str]) -> dict:
    unknown_targets = set(mapping) - TARGET_FIELDS
    if unknown_targets:
        raise ValueError(f"Unknown target fields: {sorted(unknown_targets)}")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Each uploaded column can map to only one target field.")
    renamed = df.rename(columns={source: target for target, source in mapping.items()})
    missing = sorted(REQUIRED_FIELDS - set(renamed.columns))
    if missing:
        raise ValueError(json.dumps({"error": "Missing required fields after mapping", "missing": missing}))

    clean = renamed[[column for column in renamed.columns if column in TARGET_FIELDS]].copy()
    issues = []
    numeric_fields = {
        "dispute_amount", "days_to_dispute", "customer_account_age_days",
        "customer_prior_disputes", "customer_prior_orders",
    }
    boolean_fields = {
        "delivery_confirmed", "has_delivery_proof", "ip_geolocation_match",
        "has_customer_correspondence", "has_3ds_authentication",
    }
    for field in numeric_fields:
        original = clean[field].notna().sum()
        clean[field] = pd.to_numeric(clean[field], errors="coerce")
        failures = int(original - clean[field].notna().sum())
        if failures:
            issues.append({"field": field, "rows": failures, "reason": "not numeric"})
    for field in boolean_fields:
        values = clean[field].map(_coerce_bool)
        failures = int(values.isna().sum())
        clean[field] = values
        if failures:
            issues.append({"field": field, "rows": failures, "reason": "not boolean"})
    valid = clean.dropna(subset=list(REQUIRED_FIELDS)).copy()
    invalid_ranges = (valid["dispute_amount"] < 0) | (valid["days_to_dispute"] < 0)
    if invalid_ranges.any():
        issues.append({"field": "numeric bounds", "rows": int(invalid_ranges.sum()), "reason": "negative value"})
        valid = valid.loc[~invalid_ranges]
    for field, default in {
        "dispute_id": None, "currency": "INR", "transaction_date": "1970-01-01",
        "product_category": "unknown", "shipping_method": "unknown", "card_network": "Visa",
        "reason_code_label": "",
    }.items():
        if field not in valid:
            valid[field] = default
    if "dispute_id" in valid:
        valid["dispute_id"] = valid["dispute_id"].fillna(
            pd.Series([f"UPLOAD-{index + 1:06d}" for index in range(len(valid))], index=valid.index)
        )
    valid = valid.where(pd.notna(valid), None)
    report = {
        "total_rows": int(len(df)), "usable_rows": int(len(valid)),
        "dropped_rows": int(len(df) - len(valid)), "issues": issues,
        "ground_truth_available": "outcome" in valid.columns and "reason_code" in valid.columns,
    }
    session_id = uuid.uuid4().hex
    with _lock:
        _sessions[session_id] = {"created_at": time.time(), "data": valid}
    return session_id, report


def _coerce_bool(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    if value in {"true", "1", "yes", "y", "delivered", "match", "matched"}:
        return True
    if value in {"false", "0", "no", "n", "not delivered", "no match", "unmatched"}:
        return False
    return None


def get_session(session_id: str) -> pd.DataFrame:
    _cleanup_sessions()
    with _lock:
        session = _sessions.get(session_id)
        if not session:
            raise KeyError("Upload session expired or was deleted.")
        return session["data"].copy()


def delete_session(session_id: str) -> bool:
    with _lock:
        return _sessions.pop(session_id, None) is not None