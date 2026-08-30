"""Vercel Serverless Entrypoint for Chargeback Evidence Auto-Responder API."""

import os
import sys
import json
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure parent root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

app = FastAPI(
    title="Chargeback Evidence Auto-Responder API",
    description="Defense-only representment pipeline — Razorpay AI Buildathon, Track 02: AI Risk Manager"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Chargeback Evidence Auto-Responder API"}


@app.get("/api/metrics")
def get_metrics():
    metrics_path = os.path.join(PROJECT_ROOT, "results", "metrics.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics not generated yet.")
    with open(metrics_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@app.get("/api/predictions")
def get_predictions():
    preds_path = os.path.join(PROJECT_ROOT, "results", "predictions.csv")
    if not os.path.exists(preds_path):
        raise HTTPException(status_code=404, detail="Predictions not generated yet.")
    df = pd.read_csv(preds_path)
    return df.to_dict(orient="records")


@app.post("/api/process")
def process_dispute(dispute: dict):
    try:
        from src.pipeline.run import ChargebackResponder
        model_path = os.path.join(PROJECT_ROOT, "models", "classifier.pkl")
        responder = ChargebackResponder(model_path=model_path)
        result = responder.process(dispute)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
