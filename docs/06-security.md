# Phase 6 — Security Architecture & Threat Model

## Threat Matrix

| Threat | Attack Surface | Impact | Mitigation | Residual Risk |
|---|---|---|---|---|
| PII Exposure | API payloads / log files | Leakage of customer personal data | 100% synthetic dataset via `Faker(en_IN)`. No real PII logged or stored. | Low |
| Raw Card Data Leakage | Payment webhooks | PCI-DSS non-compliance | Raw PANs/CVVs are masked/tokenized upstream. System only accepts match booleans (`avs_cvv_match`). | Negligible |
| Automated Malicious Disputes | `POST /api/disputes` | Resource exhaustion / API abuse | Input validation via Pydantic; rate limiting header configuration; fail-closed template logic. | Low |
| Fraudulent Auto-Submission | Model misclassification | Financial loss due to invalid representment | Multi-gate threshold requirement: confidence $\ge 0.70$ AND evidence strength $\ge 0.60$ AND compelling hits $\ge 2$. | Low |
| Prompt / Template Injection | Customer correspondence field | Malformed response rendering | Jinja2 auto-escaping enabled; deterministic rule mapping dictates template selection. | Low |

## Defense-Only Guardrails
1. **No Dispute Generation**: System only responds defensively to incoming chargeback webhooks.
2. **Deterministic Rules**: Evidence matching follows fixed card-network rules, preventing ML hallucination of required documents.
3. **Kill Switch**: `AUTO_RESPOND_CONFIDENCE = 1.0` instantly disables all auto-responses, routing 100% of disputes to human analysts.
