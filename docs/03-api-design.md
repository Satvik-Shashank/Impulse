# Phase 3 — API Design & Interface Specifications

The platform exposes a RESTful HTTP API built with FastAPI, fully compliant with OpenAPI 3.0 standards.

## Endpoints Summary

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Liveness & readiness health check |
| `/api/metrics` | GET | Static evaluation results from held-out test set |
| `/api/predictions` | GET | Test set predictions CSV exported as JSON array |
| `/api/disputes` | POST | Submit new dispute JSON; runs full AI pipeline & returns decision |
| `/api/disputes/{dispute_id}` | GET | Retrieve processed dispute by ID |
| `/api/disputes` | GET | Paginated dispute listing with filters (`action`, `reason_code`) |
| `/api/dashboard/summary` | GET | Aggregate metrics for dashboard overview |
| `/api/monitoring/drift` | GET | Rolling statistics snapshot for drift monitoring |
| `/api/process` | POST | Legacy backward-compatible endpoint |

## Payload Schema Example (`POST /api/disputes`)

### Request
```json
{
  "dispute_id": "DSP-2026-00142",
  "reason_code_label": "Other Fraud - Card Absent Environment",
  "card_network": "Visa",
  "dispute_amount": 12499.00,
  "currency": "INR",
  "transaction_date": "2026-06-15",
  "days_to_dispute": 35,
  "product_category": "electronics",
  "shipping_method": "express",
  "delivery_confirmed": true,
  "has_delivery_proof": true,
  "ip_geolocation_match": true,
  "avs_cvv_match": "both_match",
  "customer_account_age_days": 45,
  "customer_prior_disputes": 0,
  "customer_prior_orders": 3,
  "has_customer_correspondence": false,
  "has_3ds_authentication": true
}
```

### Response
```json
{
  "dispute_id": "DSP-2026-00142",
  "classification": {
    "predicted_reason_code": "10.4",
    "confidence": 0.942,
    "top_k_predictions": [
      { "reason_code": "10.4", "confidence": 0.942 },
      { "reason_code": "13.1", "confidence": 0.031 },
      { "reason_code": "4837", "confidence": 0.014 }
    ]
  },
  "evidence": {
    "evidence_strength": 0.83,
    "compelling_hits": 3,
    "compelling_total": 3,
    "auto_respond_eligible": true
  },
  "win_probability": 0.91,
  "expected_value_inr": 1875.00,
  "response": {
    "action": "AUTO_SUBMIT",
    "response_text": "...rendered Jinja2 template..."
  },
  "reasoning": [
    "Reason code classified as '10.4' with 94.2% calibrated confidence.",
    "Evidence strength: 83.0% (3/3 compelling pieces matched).",
    "Calibrated win probability: 91.0%.",
    "Expected value of auto-response: ₹1,875.",
    "DECISION: AUTO_SUBMIT — confidence and evidence strength both exceed threshold gates."
  ]
}
```
