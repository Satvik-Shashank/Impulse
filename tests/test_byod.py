import io
import json

import pandas as pd
from fastapi.testclient import TestClient

from api.index import app
from src.api.byod import parse_content, validate_and_stage, get_session, delete_session


client = TestClient(app)


def valid_upload_frame():
    return pd.DataFrame([{
        "Txn Amount (Rs)": 5000,
        "Days Since Order": 10,
        "Delivered?": "yes",
        "Delivery Proof": "yes",
        "IP Match": "no",
        "AVS CVV Match": "both_match",
        "Account Age": 30,
        "Prior Disputes": 0,
        "Prior Orders": 3,
        "Correspondence": "no",
        "3DS": "yes",
        "Card Type": "Visa",
        "Notes": "customer email and phone number must not persist",
    }])


def test_parse_suggests_mapping_without_persisting_extra_columns():
    frame = valid_upload_frame()
    output = io.BytesIO()
    frame.to_csv(output, index=False)
    response = client.post("/api/upload/parse", files={"file": ("merchant.csv", output.getvalue(), "text/csv")})
    assert response.status_code == 200
    assert "Txn Amount (Rs)" in response.json()["columns"]
    assert response.json()["suggested_mapping"]["dispute_amount"] == "Txn Amount (Rs)"


def test_mapping_stages_only_allowlisted_columns():
    frame = valid_upload_frame()
    mapping = {
        "dispute_amount": "Txn Amount (Rs)", "days_to_dispute": "Days Since Order",
        "delivery_confirmed": "Delivered?", "has_delivery_proof": "Delivery Proof",
        "ip_geolocation_match": "IP Match", "avs_cvv_match": "AVS CVV Match",
        "customer_account_age_days": "Account Age", "customer_prior_disputes": "Prior Disputes",
        "customer_prior_orders": "Prior Orders", "has_customer_correspondence": "Correspondence",
        "has_3ds_authentication": "3DS", "card_network": "Card Type",
    }
    session_id, report = validate_and_stage(frame, mapping)
    assert report["usable_rows"] == 1
    staged = get_session(session_id)
    assert "Notes" not in staged.columns
    assert delete_session(session_id) is True


def test_mapping_reports_bad_rows():
    frame = valid_upload_frame()
    frame["Txn Amount (Rs)"] = frame["Txn Amount (Rs)"].astype(object)
    frame.loc[0, "Txn Amount (Rs)"] = "not money"
    mapping = {"dispute_amount": "Txn Amount (Rs)", "days_to_dispute": "Days Since Order",
               "delivery_confirmed": "Delivered?", "has_delivery_proof": "Delivery Proof",
               "ip_geolocation_match": "IP Match", "avs_cvv_match": "AVS CVV Match",
               "customer_account_age_days": "Account Age", "customer_prior_disputes": "Prior Disputes",
               "customer_prior_orders": "Prior Orders", "has_customer_correspondence": "Correspondence",
               "has_3ds_authentication": "3DS"}
    _, report = validate_and_stage(frame, mapping)
    assert report["usable_rows"] == 0
    assert report["dropped_rows"] == 1
    assert any(issue["field"] == "dispute_amount" for issue in report["issues"])


def test_template_is_xlsx():
    response = client.get("/api/upload/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")