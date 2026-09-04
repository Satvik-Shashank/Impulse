"""Vercel Serverless Entrypoint for Chargeback Intelligence Platform API.

All routes are served via FastAPI on Vercel Python Serverless Functions.
The frontend is served as static files from the public/ directory.
"""

import os
import sys
import json
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal, Optional
from collections import defaultdict
import time
import io
from fastapi.responses import StreamingResponse


class DisputePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispute_id: str = Field(..., min_length=1, max_length=100)
    card_network: Literal["Visa", "Mastercard"]
    dispute_amount: float = Field(..., ge=0, le=10_000_000)
    currency: Literal["INR"] = "INR"
    transaction_date: str = Field(..., min_length=8, max_length=30)
    days_to_dispute: int = Field(..., ge=0, le=3650)
    product_category: str = Field(..., min_length=1, max_length=50)
    shipping_method: str = Field(..., min_length=1, max_length=30)
    delivery_confirmed: bool = False
    has_delivery_proof: bool = False
    ip_geolocation_match: bool = False
    avs_cvv_match: Literal["both_match", "avs_only", "cvv_only", "neither"] = "neither"
    customer_account_age_days: int = Field(0, ge=0, le=100000)
    customer_prior_disputes: int = Field(0, ge=0, le=10000)
    customer_prior_orders: int = Field(0, ge=0, le=100000)
    has_customer_correspondence: bool = False
    has_3ds_authentication: bool = False
    reason_code_label: Optional[str] = Field(None, max_length=200)


_rate_window = defaultdict(list)
RATE_LIMIT = 60

# Ensure parent root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

app = FastAPI(
    title="Chargeback Intelligence & Auto-Resolution Platform API",
    description="Defense-only representment decision pipeline with cost-sensitive calibrated confidence",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def fix_vercel_rewrites(request: Request, call_next):
    # 1. Check query parameter 'path' passed by vercel rewrite: /api/index.py?path=...
    target_path = request.query_params.get("path")

    # 2. Check Vercel headers for original URI
    if not target_path:
        target_path = (
            request.headers.get("x-matched-path")
            or request.headers.get("x-forwarded-uri")
            or request.headers.get("x-original-uri")
            or request.headers.get("x-invoke-path")
        )

    # 3. Fallback to scope path
    if not target_path:
        target_path = request.scope.get("path", "")

    # Strip /api/index.py prefix if present
    if target_path.startswith("/api/index.py"):
        target_path = target_path[len("/api/index.py"):]

    if not target_path or target_path == "/":
        target_path = "/api/health"

    # Ensure /api prefix for API routes (unless static)
    if not target_path.startswith("/api") and not target_path.startswith("/static"):
        target_path = "/api/" + target_path.lstrip("/")

    request.scope["path"] = target_path
    return await call_next(request)



from fastapi.staticfiles import StaticFiles
public_dir = os.path.join(PROJECT_ROOT, "public")
if os.path.exists(public_dir):
    app.mount("/static", StaticFiles(directory=public_dir), name="static")



# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    model_path = os.path.join(PROJECT_ROOT, "models", "classifier.pkl")
    has_managed_db = bool(os.getenv("DATABASE_URL"))
    model_status = "missing"
    load_error = None
    lightgbm_importable = None
    if os.path.exists(model_path):
        from src.models.classifier import DisputeClassifier, HAS_LIGHTGBM
        lightgbm_importable = HAS_LIGHTGBM
        classifier = DisputeClassifier.load(model_path)
        model_status = "ready" if classifier.model is not None else "unavailable"
        load_error = classifier.load_error
    return {
        "status": "ok" if model_status == "ready" else "degraded",
        "service": "Chargeback Intelligence Platform",
        "version": "2.0.0",
        "model_artifact": os.path.exists(model_path),
        "model_status": model_status,
        "lightgbm_importable": lightgbm_importable,
        "model_load_error": load_error,
        "persistence": "managed" if has_managed_db else "local_development_only",
    }


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


# ── Bring Your Own Data (memory-only) ──────────────────────────────────────

@app.get("/api/upload/template")
def upload_template():
    """Download a schema template; uploaded data is never written here."""
    from src.api.byod import REQUIRED_FIELDS, OPTIONAL_FIELDS
    columns = sorted(REQUIRED_FIELDS | OPTIONAL_FIELDS)
    template = pd.DataFrame([
        {column: "" for column in columns},
        {column: "" for column in columns},
        {column: "" for column in columns},
    ])
    output = io.BytesIO()
    template.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=chargeback-upload-template.xlsx"},
    )


@app.post("/api/upload/parse")
async def parse_upload(file: UploadFile = File(...)):
    """Parse an upload in memory and return only columns and a small preview."""
    from src.api.byod import parse_content, suggest_column_mapping
    try:
        content = await file.read()
        frame = parse_content(file.filename or "", content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "filename": file.filename,
        "columns": [str(column) for column in frame.columns],
        "row_count": int(len(frame)),
        "preview": frame.head(5).where(pd.notna(frame.head(5)), None).to_dict(orient="records"),
        "suggested_mapping": suggest_column_mapping([str(column) for column in frame.columns]),
    }


@app.post("/api/upload/apply-mapping")
async def apply_upload_mapping(file: UploadFile = File(...), mapping: str = Form(...)):
    """Map, validate, and stage only schema-approved rows in process memory."""
    from src.api.byod import parse_content, validate_and_stage
    try:
        parsed_mapping = json.loads(mapping)
        if not isinstance(parsed_mapping, dict):
            raise ValueError("mapping must be a JSON object")
        content = await file.read()
        frame = parse_content(file.filename or "", content)
        session_id, report = validate_and_stage(frame, parsed_mapping)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not validate upload: {exc}")
    return {"session_id": session_id, "filename": file.filename, "validation_report": report,
            "usable_row_count": report["usable_rows"],
            "retention": "memory-only; expires after 1 hour"}


@app.delete("/api/upload/{session_id}")
def delete_upload(session_id: str):
    from src.api.byod import delete_session
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Upload session not found or already expired.")
    return {"deleted": True}


@app.post("/api/upload/{session_id}/analyze")
def analyze_upload(session_id: str):
    from src.api.byod import get_session
    from src.pipeline.run import ChargebackResponder
    try:
        frame = get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    responder = ChargebackResponder(
        model_path=os.path.join(PROJECT_ROOT, "models", "classifier.pkl"),
        win_model_path=os.path.join(PROJECT_ROOT, "models", "win_predictor.pkl"),
    )
    predictions = []
    for index, row in frame.iterrows():
        payload = row.to_dict()
        payload = {key: value for key, value in payload.items()
                   if key in DisputePayload.model_fields}
        try:
            validated = DisputePayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=f"Staged row {index} is invalid: {exc.errors()}")
        predictions.append(responder.process(validated.model_dump()))
    metrics = None
    metrics_available = False
    if "outcome" in frame.columns and "reason_code" in frame.columns:
        from sklearn.metrics import classification_report, roc_auc_score
        actual = frame["reason_code"].astype(str).tolist()
        predicted = [item["classification"]["predicted_reason_code"] for item in predictions]
        metrics = {
            "reason_code_accuracy": sum(a == p for a, p in zip(actual, predicted)) / len(actual),
            "reason_code_report": classification_report(actual, predicted, output_dict=True, zero_division=0),
        } if actual else None
        outcomes = frame["outcome"].astype(str).tolist()
        win_probabilities = [item["win_probability"] for item in predictions]
        if len(set(outcomes)) == 2 and all(value is not None for value in win_probabilities):
            metrics["win_prediction_auc"] = roc_auc_score(
                [outcome == "merchant_won" for outcome in outcomes], win_probabilities
            )
        metrics_available = metrics is not None
    return {
        "session_id": session_id, "predictions": predictions, "metrics": metrics,
        "metrics_available": metrics_available,
        "evaluation_note": "Metrics unavailable without both reason_code and outcome ground truth."
        if not metrics_available else "Evaluation uses the uploaded ground-truth columns.",
        "data_source": "uploaded_data",
    }


# ── Process / Submit dispute (live pipeline) ───────────────────────────────

@app.post("/api/disputes")
def create_dispute(dispute: DisputePayload, request: Request):
    """Ingest a dispute, run the full AI pipeline, persist result, and return."""
    client = request.client.host if request.client else "unknown"
    now = time.time()
    _rate_window[client] = [timestamp for timestamp in _rate_window[client] if now - timestamp < 60]
    if len(_rate_window[client]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _rate_window[client].append(now)
    dispute = dispute.model_dump()
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
        except Exception as exc:
            result["persistence"] = {"status": "degraded", "error": str(exc)}

        # Log to monitoring
        try:
            monitor = MonitoringLog()
            monitor.log_prediction(result)
        except Exception as exc:
            result["monitoring"] = {"status": "degraded", "error": str(exc)}

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Legacy route — backward compatibility
@app.post("/api/process")
def process_dispute_legacy(dispute: DisputePayload, request: Request):
    """Legacy endpoint — redirects to /api/disputes."""
    return create_dispute(dispute, request)


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


# ── Static Frontend Mount for Local Viewing ───────────────────────────────

if os.path.exists(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")

