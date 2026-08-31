# Phase 9 — Failure Mode Analysis & Mitigation

| Component | Failure Mode | Detection | Impact | Recovery / Fallback | User Experience |
|---|---|---|---|---|---|
| Evidence Retriever | Missing / incomplete evidence fields | Rule table check (`compelling_hits < 2`) | Low auto-submit eligibility | Route to `HUMAN_REVIEW` | High-visibility warning tag in dashboard |
| Classifier | Low confidence prediction ($< 0.70$) | Threshold comparison | High risk of false-positive submission | Route to `HUMAN_REVIEW` | Flagged for manual analyst verification |
| Ingestion API | Malformed / unrecognized reason code | Pydantic validation error | Failed request | Fallback to `generic.j2` template with `auto_respond_eligible = False` | Clean HTTP 400 error message |
| Database | SQLite lock contention / write error | SQLAlchemy Exception | Storage failure | Pipeline returns response object to caller regardless | Alert logged; API response succeeds |
| Model Drift | Distribution shift in incoming disputes | Monitoring log rolling stats | Degraded classifier accuracy | Trigger alert; retrain model on new batch | Dashboard monitoring tab highlights drift |
