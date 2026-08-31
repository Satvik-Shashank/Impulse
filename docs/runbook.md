# Operations Runbook

## Daily Operational Tasks

### 1. Monitoring Model Health
Check the `/api/monitoring/drift` endpoint or view the **Model Monitoring** tab in the dashboard to review:
- `avg_confidence`: Should remain $\ge 0.75$. Drop below $0.65$ signals potential drift.
- `avg_evidence_strength`: Should remain $\ge 0.70$.
- `auto_respond_rate`: Typical baseline is $50\%\text{--}70\%$.

### 2. Retraining Pipeline
To retrain both models on fresh dispute data:
```bash
.venv\Scripts\python -m src.data.generate_disputes --n 5000
.venv\Scripts\python -m src.evaluate
```

### 3. Running Test Suite
Before committing any changes:
```bash
.venv\Scripts\pytest
```
