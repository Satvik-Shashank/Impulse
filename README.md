# Enterprise Chargeback Evidence Auto-Responder

Defense-only ML pipeline & Full-Stack Dispute Management Platform for the **Razorpay AI Buildathon — Track 02: AI Risk Manager**.

## What it does

This enterprise web application provides a defense-only chargeback representment auto-responder backed by an SQLite database (`data/chargebacks.db`), a LightGBM multi-class reason code classifier with Platt calibration, rule-based evidence scoring, Jinja2 template rendering, and quantitative cost optimization.

### Key Capabilities

1. **Persistent SQLite Database (`src/db/`)**:
   - Stores incoming disputes, merchant evidence document attachments (`EvidenceAttachmentModel`), decision audit logs (`DecisionAuditLogModel`), and merchant approvals.
2. **Interactive Dispute Submission**:
   - Merchants can manually submit custom transaction payloads, upload evidence documents (receipts, delivery proofs, 3DS logs), and re-evaluate evidence strength in real-time.
3. **Calibrated ML Reason-Code Classifier**:
   - Predicts dispute reason code (LightGBM, feature-conditioned prior) and returns Platt-calibrated confidence probabilities.
4. **Rule-Based Evidence Retriever**:
   - Scores available evidence against public Visa & Mastercard representment specifications (auditable by design).
5. **Network-Compliant Jinja2 Template Generator**:
   - Automatically drafts formal representment responses.
6. **Quantitative Cost Optimization**:
   - Computes rupee-denominated FP/FN/TP cost accounting, optimal confidence gates, and baseline comparisons (Fight Everything vs Fight Nothing vs System).

## Architecture

- **Backend**: FastAPI (`api/index.py`), SQLAlchemy ORM (`src/db/models.py`), LightGBM (`src/models/classifier.py`), Jinja2 (`src/pipeline/response_generator.py`).
- **Database**: SQLite (`data/chargebacks.db`).
- **Frontend**: Vanilla HTML5, CSS3 (Obsidian Glassmorphic Theme), JavaScript (Fetch API, zero framework bloat).
- **Deployment**: Vercel Serverless Function (`@vercel/python` + `@vercel/static`).

## Setup & Local Execution

    python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

### 1. Run Data Generation, Training & Evaluation

    python -m src.data.generate_disputes
    python -m src.train
    python -m src.evaluate --test-set data/disputes_test.csv --output results/

### 2. Launch Local Enterprise Web Application & API

    python -m uvicorn api.index:app --reload --port 8000

Open your browser at: **`http://localhost:8000/public/index.html`** (or `http://localhost:8000/index.html` when deployed on Vercel).

## Test Suite

    pytest -q

Runs all unit tests, classifier regression guards, and executable failure-mode documentation tests.

## Cost Assumptions & Disclaimer

All ₹ cost figures (`COST_FP = ₹1,000`, `COST_FN = ₹350`, `SAVINGS_TP = ₹2,250`) are working modeling assumptions used for decision policy optimization, not cited industry statistics.
