"""Integration tests for the FastAPI endpoint routes."""

from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_metrics():
    response = client.get("/api/metrics")
    # May return 200 or 404 depending on whether evaluate has run
    assert response.status_code in (200, 404)


def test_api_create_dispute():
    sample_payload = {
        "dispute_id": "DSP-TEST-001",
        "reason_code_label": "Fraud - Card Absent",
        "card_network": "Visa",
        "dispute_amount": 5000.00,
        "currency": "INR",
        "transaction_date": "2026-08-01",
        "days_to_dispute": 15,
        "product_category": "electronics",
        "shipping_method": "express",
        "delivery_confirmed": True,
        "has_delivery_proof": True,
        "ip_geolocation_match": True,
        "avs_cvv_match": "both_match",
        "customer_account_age_days": 60,
        "customer_prior_disputes": 0,
        "customer_prior_orders": 5,
        "has_customer_correspondence": False,
        "has_3ds_authentication": True,
    }
    response = client.post("/api/disputes", json=sample_payload)
    assert response.status_code == 200
    data = response.json()
    assert "dispute_id" in data
    assert "classification" in data
    assert "win_probability" in data
    assert "expected_value_inr" in data
    assert "reasoning" in data
    assert "top_k_predictions" in data["classification"]


def test_api_get_disputes_list():
    response = client.get("/api/disputes")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


def test_api_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_disputes" in data


def test_api_monitoring_drift():
    response = client.get("/api/monitoring/drift")
    assert response.status_code == 200
    data = response.json()
    assert "window_size" in data


def test_api_rejects_unknown_fields():
    response = client.post("/api/disputes", json={"dispute_id": "x", "card_number": "4111111111111111"})
    assert response.status_code == 422


def test_api_rejects_negative_amount():
    response = client.post("/api/disputes", json={
        "dispute_id": "DSP-TEST-NEG", "card_network": "Visa", "dispute_amount": -1,
        "transaction_date": "2026-08-01", "days_to_dispute": 1,
        "product_category": "electronics", "shipping_method": "standard",
    })
    assert response.status_code == 422


def test_api_rejects_blank_numeric_field_with_validation_error():
    response = client.post("/api/disputes", json={
        "dispute_id": "DSP-TEST-BLANK", "card_network": "Mastercard", "dispute_amount": 1994.18,
        "transaction_date": "2026-08-01", "days_to_dispute": 10,
        "product_category": "beauty", "shipping_method": "standard",
        "customer_account_age_days": "",
    })
    assert response.status_code == 422
    assert "customer_account_age_days" in response.text
