"""Synthetic dispute data generator (feature-conditioned).

Generates realistic (but 100% synthetic — no PII) chargeback dispute records.

Unlike a naive generator that samples reason_code independently of the
transaction features, this version draws the feature profile FIRST (is this
transaction fraud-flavored or not?) and then samples reason_code conditional
on that profile. This is what makes the reason-code classifier's job a real,
learnable problem rather than an unconditional prior guess — and it's what
makes the resulting precision/recall numbers meaningful to report.

Run:
    python -m src.data.generate_disputes
"""

import os
import numpy as np
import pandas as pd
from faker import Faker

fake = Faker("en_IN")  # Indian locale for BFSI context
np.random.seed(42)
Faker.seed(42)

# ── Reason Code Taxonomy (Visa + Mastercard) ──
REASON_CODES = {
    "10.4": {"label": "Fraud - Card Absent", "network": "Visa",
             "evidence_needed": ["avs_cvv", "ip_match", "delivery_proof", "device_fingerprint"],
             "merchant_win_rate": 0.22, "is_fraud_flavored": True},
    "10.5": {"label": "Fraud - Counterfeit", "network": "Visa",
             "evidence_needed": ["emv_chip_data", "pin_verification"],
             "merchant_win_rate": 0.15, "is_fraud_flavored": True},
    "13.1": {"label": "Merchandise Not Received", "network": "Visa",
             "evidence_needed": ["shipping_confirmation", "delivery_proof", "tracking_url"],
             "merchant_win_rate": 0.45, "is_fraud_flavored": False},
    "13.3": {"label": "Not as Described", "network": "Visa",
             "evidence_needed": ["product_description", "customer_comms", "return_policy"],
             "merchant_win_rate": 0.35, "is_fraud_flavored": False},
    "13.6": {"label": "Credit Not Processed", "network": "Visa",
             "evidence_needed": ["refund_receipt", "refund_arn", "policy_terms"],
             "merchant_win_rate": 0.55, "is_fraud_flavored": False},
    "4837": {"label": "No Cardholder Authorization", "network": "Mastercard",
             "evidence_needed": ["3ds_authentication", "avs_cvv", "ip_match"],
             "merchant_win_rate": 0.18, "is_fraud_flavored": True},
    "4853": {"label": "Cardholder Dispute - Defective", "network": "Mastercard",
             "evidence_needed": ["product_description", "quality_cert", "customer_comms"],
             "merchant_win_rate": 0.30, "is_fraud_flavored": False},
    "4855": {"label": "Goods or Services Not Provided", "network": "Mastercard",
             "evidence_needed": ["shipping_confirmation", "delivery_proof", "signed_receipt"],
             "merchant_win_rate": 0.42, "is_fraud_flavored": False},
    "4863": {"label": "Cardholder Does Not Recognize", "network": "Mastercard",
             "evidence_needed": ["billing_descriptor", "customer_comms", "ip_match"],
             "merchant_win_rate": 0.25, "is_fraud_flavored": True},
    "4860": {"label": "Credit Not Processed (MC)", "network": "Mastercard",
             "evidence_needed": ["refund_receipt", "refund_arn", "policy_terms"],
             "merchant_win_rate": 0.50, "is_fraud_flavored": False},
}

_RC_KEYS = list(REASON_CODES.keys())
FRAUD_CODES = [k for k, v in REASON_CODES.items() if v["is_fraud_flavored"]]
NONFRAUD_CODES = [k for k, v in REASON_CODES.items() if not v["is_fraud_flavored"]]

# Base priors *within* each flavor bucket (must each sum to 1.0)
_FRAUD_PROBS = [0.35, 0.10, 0.30, 0.25]           # order matches 4 FRAUD_CODES (10.4, 10.5, 4837, 4863)
_NONFRAUD_PROBS = [0.25, 0.15, 0.10, 0.20, 0.15, 0.15]  # order matches 6 NONFRAUD_CODES (13.1, 13.3, 13.6, 4853, 4855, 4860)

PRODUCT_CATEGORIES = ["electronics", "fashion", "grocery", "home", "books",
                      "beauty", "sports", "toys", "automotive", "health"]
SHIPPING_METHODS = ["standard", "express", "same_day", "pickup"]

# Overall mix: what fraction of disputes are fraud-flavored vs not.
P_FRAUD_FLAVOR = 0.40


def generate_dispute(dispute_id: int) -> dict:
    """Generate one synthetic dispute: features first, reason code conditional on them."""

    # ── Step 1: decide the underlying "flavor" of this dispute ──
    is_fraud_code = np.random.random() < P_FRAUD_FLAVOR

    # ── Step 2: draw transaction features CONDITIONAL on the flavor ──
    amount = np.random.lognormal(mean=7.5 if is_fraud_code else 6.8, sigma=1.2)
    amount = round(min(amount, 500000), 2)  # Cap at Rs 5L

    days_to_dispute = int(np.random.exponential(scale=25 if is_fraud_code else 15))
    days_to_dispute = min(days_to_dispute, 120)

    txn_date = fake.date_between(start_date="-6m", end_date="-1m")

    # Fraud-flavored disputes: less delivery/auth evidence available, faster filing.
    delivery_confirmed = np.random.random() > (0.55 if is_fraud_code else 0.10)
    has_delivery_proof = delivery_confirmed and (np.random.random() > (0.35 if is_fraud_code else 0.15))
    ip_match = np.random.random() > (0.65 if is_fraud_code else 0.08)

    avs_cvv = np.random.choice(
        ["both_match", "avs_only", "cvv_only", "neither"],
        p=[0.20, 0.20, 0.15, 0.45] if is_fraud_code else [0.75, 0.13, 0.08, 0.04],
    )

    has_3ds = np.random.random() > (0.75 if is_fraud_code else 0.25)
    prior_disputes = int(np.random.poisson(0.6 if is_fraud_code else 0.1))
    has_customer_correspondence = np.random.random() > (0.75 if is_fraud_code else 0.45)
    customer_account_age_days = int(np.random.exponential(90 if is_fraud_code else 220))
    product_category = str(np.random.choice(PRODUCT_CATEGORIES))
    shipping_method = str(np.random.choice(SHIPPING_METHODS))

    # ── Step 3: NOW sample reason_code, conditional on the flavor already drawn ──
    if is_fraud_code:
        rc = np.random.choice(FRAUD_CODES, p=_FRAUD_PROBS)
    else:
        rc = np.random.choice(NONFRAUD_CODES, p=_NONFRAUD_PROBS)

    rc_info = REASON_CODES[rc]

    # Add reason-code-specific signal after bucket conditioning so codes within
    # the same fraud/non-fraud group remain distinguishable.
    if rc == "10.4":
        product_category, shipping_method = "electronics", "express"
        ip_match, has_3ds = False, False
    elif rc == "10.5":
        product_category, shipping_method = "automotive", "pickup"
        avs_cvv, has_3ds = "neither", False
    elif rc == "13.1":
        shipping_method, delivery_confirmed, has_delivery_proof = "standard", False, False
    elif rc == "13.3":
        product_category, has_customer_correspondence = "fashion", True
    elif rc == "13.6":
        product_category, has_customer_correspondence = "home", True
        days_to_dispute = max(days_to_dispute, 45)
    elif rc == "4837":
        has_3ds, avs_cvv = False, "neither"
    elif rc == "4853":
        product_category, has_customer_correspondence = "beauty", True
    elif rc == "4855":
        shipping_method, delivery_confirmed, has_delivery_proof = "standard", False, False
    elif rc == "4860":
        product_category, has_customer_correspondence = "grocery", True
        days_to_dispute = max(days_to_dispute, 45)
    elif rc == "4863":
        customer_account_age_days = min(customer_account_age_days, 30)
        prior_disputes = max(prior_disputes, 1)

    # ── Step 4: outcome depends on reason code's base win rate + evidence quality ──
    evidence_score = sum([
        has_delivery_proof * 0.25,
        ip_match * 0.15,
        (avs_cvv == "both_match") * 0.20,
        delivery_confirmed * 0.15,
        (days_to_dispute < 30) * 0.10,
        has_3ds * 0.10,
        has_customer_correspondence * 0.05,
    ])

    win_prob = rc_info["merchant_win_rate"] + evidence_score * 0.5
    win_prob = np.clip(win_prob, 0.05, 0.95)
    outcome = "merchant_won" if np.random.random() < win_prob else "merchant_lost"

    return {
        "dispute_id": f"DSP-{dispute_id:06d}",
        "reason_code": rc,
        "reason_code_label": rc_info["label"],
        "card_network": rc_info["network"],
        "dispute_amount": amount,
        "currency": "INR",
        "transaction_date": str(txn_date),
        "days_to_dispute": days_to_dispute,
        "product_category": product_category,
        "shipping_method": shipping_method,
        "delivery_confirmed": bool(delivery_confirmed),
        "has_delivery_proof": bool(has_delivery_proof),
        "ip_geolocation_match": bool(ip_match),
        "avs_cvv_match": avs_cvv,
        "customer_account_age_days": customer_account_age_days,
        "customer_prior_disputes": prior_disputes,
        "customer_prior_orders": int(np.random.poisson(2 if is_fraud_code else 6)),
        "has_customer_correspondence": bool(has_customer_correspondence),
        "has_3ds_authentication": bool(has_3ds),
        "evidence_needed": rc_info["evidence_needed"],
        "outcome": outcome,
    }


def build_dataset(n: int = 5000) -> pd.DataFrame:
    """Build a DataFrame of ``n`` synthetic disputes."""
    records = [generate_dispute(i) for i in range(n)]
    return pd.DataFrame(records)


def main(n: int = 5000, out_dir: str = "data") -> None:
    from sklearn.model_selection import train_test_split

    df = build_dataset(n)
    train, temp = train_test_split(
        df, test_size=0.3, stratify=df["reason_code"], random_state=42)
    val, test = train_test_split(
        temp, test_size=0.5, stratify=temp["reason_code"], random_state=42)

    os.makedirs(out_dir, exist_ok=True)
    train.to_csv(os.path.join(out_dir, "disputes_train.csv"), index=False)
    val.to_csv(os.path.join(out_dir, "disputes_val.csv"), index=False)
    test.to_csv(os.path.join(out_dir, "disputes_test.csv"), index=False)

    print(f"Generated: train={len(train)}, val={len(val)}, test={len(test)}")
    print(f"Reason code distribution:\n{df['reason_code'].value_counts()}")


if __name__ == "__main__":
    main()
