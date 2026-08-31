"""Vercel Serverless Entrypoint for Chargeback Intelligence Platform API.

All routes are served via FastAPI on Vercel Python Serverless Functions.
The frontend is served as static files from the public/ directory.
"""

import os
import sys
import json
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Ensure parent root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

app = FastAPI(
    title="Chargeback Intelligence & Auto-Resolution Platform API",
    description="Defense-only representment pipeline — Razorpay AI Buildathon, Track 02: AI Risk Manager",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Chargeback Intelligence Platform", "version": "2.0.0"}


# ── Metrics (static evaluation results) ────────────────────────────────────

@app.get("/api/metrics")
def get_metrics():
    metrics_path = os.path.join(PROJECT_ROOT, "results", "metrics.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics not generated yet. Run: python -m src.evaluate")
    with open(metrics_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── Predictions (static eval predictions) ──────────────────────────────────

@app.get("/api/predictions")
def get_predictions():
    preds_path = os.path.join(PROJECT_ROOT, "results", "predictions.csv")
    if not os.path.exists(preds_path):
        raise HTTPException(status_code=404, detail="Predictions not generated yet.")
    df = pd.read_csv(preds_path)
    return df.to_dict(orient="records")


# ── Process / Submit dispute (live pipeline) ───────────────────────────────

@app.post("/api/disputes")
def create_dispute(dispute: dict):
    """Ingest a dispute, run the full AI pipeline, persist result, and return."""
    try:
        from src.pipeline.run import ChargebackResponder
        from src.api.storage import DisputeStore
        from src.api.monitoring import MonitoringLog

        model_path = os.path.join(PROJECT_ROOT, "models", "classifier.pkl")
        win_model_path = os.path.join(PROJECT_ROOT, "models", "win_predictor.pkl")

        responder = ChargebackResponder(model_path=model_path, win_model_path=win_model_path)
        result = responder.process(dispute)

        # Persist to DB
        try:
            store = DisputeStore()
            store.save_result(dispute, result)
        except Exception:
            pass  # DB write failure should not block API response

        # Log to monitoring
        try:
            monitor = MonitoringLog()
            monitor.log_prediction(result)
        except Exception:
            pass

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Legacy route — backward compatibility
@app.post("/api/process")
def process_dispute_legacy(dispute: dict):
    """Legacy endpoint — redirects to /api/disputes."""
    return create_dispute(dispute)


# ── Get single dispute by ID ──────────────────────────────────────────────

@app.get("/api/disputes/{dispute_id}")
def get_dispute(dispute_id: str):
    try:
        from src.api.storage import DisputeStore
        store = DisputeStore()
        result = store.get_dispute(dispute_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Dispute '{dispute_id}' not found.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── List disputes (paginated) ─────────────────────────────────────────────

@app.get("/api/disputes")
def list_disputes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    reason_code: Optional[str] = None,
):
    try:
        from src.api.storage import DisputeStore
        store = DisputeStore()
        return store.list_disputes(page=page, per_page=per_page,
                                   action=action, reason_code=reason_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard summary ─────────────────────────────────────────────────────

@app.get("/api/dashboard/summary")
def dashboard_summary():
    try:
        from src.api.storage import DisputeStore
        store = DisputeStore()
        return store.get_dashboard_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Monitoring drift ──────────────────────────────────────────────────────

@app.get("/api/monitoring/drift")
def monitoring_drift(window: int = Query(200, ge=10, le=5000)):
    try:
        from src.api.monitoring import MonitoringLog
        monitor = MonitoringLog()
        return monitor.compute_drift_snapshot(window=window)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
