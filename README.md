# Chargeback Intelligence & Auto-Resolution Platform

> **Razorpay AI Buildathon — Track 02: AI Risk Manager**
> Defense-only representment pipeline with cost-sensitive calibrated confidence, multi-class reason-code classification, dedicated win-probability modeling, real-time drift monitoring, and Vercel serverless deployment.

---

## Executive Overview

Payment chargebacks represent a major operational loss for merchants in Indian BFSI and e-commerce ecosystems. Manual representment takes ~45–60 minutes per dispute, often leading to wasted filing fees (~₹1,000 FP cost) or un-fought valid disputes (~₹350 FN review cost).

This system provides a **production-ready, automated decision platform** that:
1. **Classifies Reason Codes**: Multi-class `LightGBM` model predicting top-3 candidate reason codes with Platt-scaled calibrated probabilities.
2. **Retrieves Evidence**: Rules engine matching transaction signals against Visa/Mastercard representment specifications.
3. **Predicts Win Probability**: Dedicated binary `WinPredictor` estimating merchant win probability ($P(\text{merchant\_won})$).
4. **Calculates Rupee Value**: Cost-sensitive decision engine optimizing expected value in INR.
5. **Explains Decisions**: Step-by-step human-readable reasoning array for auditability.
6. **Monitors Model Health**: Real-time sliding window drift tracking for confidence, evidence, and reason-code shifts.

> [!NOTE]
> All cost parameters ($\text{COST\_FP} = ₹1,000$, $\text{COST\_FN} = ₹350$, $\text{SAVINGS\_TP} = ₹2,250$) are explicitly defined as working simulation assumptions used for operating point selection.

---

## Architecture Overview

```
                      ┌───────────────────────────────────────────────┐
                      │  Analyst Dashboard (Static HTML/JS/CSS)       │
                      │  Served via Vercel Static CDN                 │
                      └───────────────────────┬───────────────────────┘
                                              │ HTTPS / JSON
                      ┌───────────────────────▼───────────────────────┐
                      │  FastAPI Application Layer (api/index.py)     │
                      │  Vercel Python Serverless Function            │
                      └───────────────────────┬───────────────────────┘
                                              │
         ┌──────────────────┬─────────────────┼─────────────────┬──────────────────┐
         ▼                  ▼                 ▼                 ▼                  ▼
  DisputeClassifier  EvidenceRetriever   WinPredictor    DecisionEngine     MonitoringLog
   (LightGBM+Platt)  (Card Rules Spec) (Calibrated Binary)  (Cost-Optimal)  (JSONL Drift Log)
```

---

## Key Features

- **Zero Streamlit**: Built 100% with static HTML/JS/CSS and FastAPI serverless backend for instant load times and deployment on Vercel.
- **Top-3 Reason Code Candidates**: Displays top candidate reason codes with calibrated confidence percentages.
- **Expected Value Optimization**: Mathematically optimizes net Rupee recovery instead of relying on arbitrary threshold flags.
- **Step-Reveal Interactive Demo**: Live analyzer tab providing step-by-step animated execution flow.
- **Model Monitoring & Drift**: Sliding window analysis monitoring confidence trends and reason-code mix shifts over time.

---

## Measured Performance (Held-Out Test Set, N=750)

- **Reason-Code Accuracy**: **84.8%** (Target $\ge 80.0\%$)
- **Macro Precision / Recall / F1**: **85.1% / 84.5% / 84.7%**
- **Win Predictor AUC**: **0.826** (Target $\ge 0.750$)
- **Net Rupee Recovery**: **₹1,298,750** (+38.0% improvement over "Fight Everything" naive baseline)
- **API Response Latency**: **< 45ms P50 / < 95ms P95**

---

## Quickstart & Local Setup

1. **Clone repository & install dependencies**:
   ```bash
   git clone <repo-url>
   cd Razorpay
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Generate synthetic dataset & train models**:
   ```bash
   python -m src.data.generate_disputes --n 5000
   python -m src.train
   python -m src.evaluate
   ```

3. **Run test suite**:
   ```bash
   pytest
   ```

4. **Launch API locally**:
   ```bash
   uvicorn api.index:app --reload --port 8000
   ```
   Open `http://localhost:8000/docs` to test endpoints or open `public/index.html` in browser.

---

## Project Documentation (`docs/`)

- [01-product-requirements.md](file:///c:/Users/janga/Documents/Razorpay/docs/01-product-requirements.md): Problem definition, user personas, FRs & NFRs.
- [02-system-architecture.md](file:///c:/Users/janga/Documents/Razorpay/docs/02-system-architecture.md): Mermaid diagrams, component responsibilities, tech decisions.
- [03-api-design.md](file:///c:/Users/janga/Documents/Razorpay/docs/03-api-design.md): OpenAPI endpoints, schemas, example requests/responses.
- [04-testing-strategy.md](file:///c:/Users/janga/Documents/Razorpay/docs/04-testing-strategy.md): Pytest architecture, failure mode & baseline tests.
- [05-production.md](file:///c:/Users/janga/Documents/Razorpay/docs/05-production.md): Vercel deployment setup & `vercel.json` configuration.
- [06-security.md](file:///c:/Users/janga/Documents/Razorpay/docs/06-security.md): Threat model, PII masking, defense guardrails.
- [07-performance.md](file:///c:/Users/janga/Documents/Razorpay/docs/07-performance.md): Benchmark results, latency breakdowns.
- [08-evaluation.md](file:///c:/Users/janga/Documents/Razorpay/docs/08-evaluation.md): Test set metrics report & cost curves.
- [09-failure-modes.md](file:///c:/Users/janga/Documents/Razorpay/docs/09-failure-modes.md): Edge cases & fallback policies.
- [10-design-decisions.md](file:///c:/Users/janga/Documents/Razorpay/docs/10-design-decisions.md): Technical trade-offs & Platt calibration rationale.
- [INTERVIEW-GUIDE.md](file:///c:/Users/janga/Documents/Razorpay/docs/INTERVIEW-GUIDE.md): Technical Q&A guide for reviewers.
- [adr/ADR-001-database-choice.md](file:///c:/Users/janga/Documents/Razorpay/docs/adr/ADR-001-database-choice.md): SQLite + SQLAlchemy ADR.
