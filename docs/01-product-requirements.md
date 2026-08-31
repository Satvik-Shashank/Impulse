# Phase 1 — Product Definition: Chargeback Intelligence Platform

## Problem Statement
In Indian BFSI and e-commerce ecosystems, payment chargebacks (disputes) represent a major operational drag for merchants. When a cardholder contests a transaction, merchants face tight card-network deadlines to submit compelling evidence. 

Manual representment is inefficient: operations teams spend 45–60 minutes per dispute compiling proof, often submitting weak responses for unwinnable disputes (wasting non-refundable filing fees of ~₹1,000) or forfeiting valid cases (~₹350 ops labor cost per lost case). 

## Users & Stakeholders
1. **Risk Ops Managers**: Require executive visibility into auto-resolution performance, net value recovered, and false-positive/negative error rates.
2. **Dispute Analysts**: Need an automated assistant that classifies reason codes, checks available evidence against card network specs, predicts win probability, and generates complete Jinja2 response packages.
3. **Engineering / ML Team**: Require observable model performance, drift monitoring, and transparent cost-sensitive operating point selection.

## Functional Requirements
- **FR-001**: The system SHALL ingest raw transaction and dispute JSON webhooks.
- **FR-002**: The classifier SHALL predict the top-3 candidate reason codes with Platt-scaled calibrated probabilities.
- **FR-003**: The evidence retriever SHALL match transaction signals against Visa/Mastercard representment rule tables.
- **FR-004**: The win predictor SHALL compute a calibrated probability of merchant victory ($P(\text{merchant\_won})$).
- **FR-005**: The decision engine SHALL calculate expected financial value in INR and route to `AUTO_SUBMIT` or `HUMAN_REVIEW`.
- **FR-006**: The system SHALL output a step-by-step human-readable reasoning array for auditability.
- **FR-007**: The dashboard SHALL display live metrics, case exploration, model performance curves, and distribution drift.

## Non-Functional Requirements
- **NFR-001 (Performance)**: Sub-second end-to-end pipeline execution (< 500ms P95 latency).
- **NFR-002 (Security)**: Zero PII exposure; strict synthetic data usage; defense-only guardrails (no dispute generation).
- **NFR-003 (Observability)**: Append-only JSONL prediction log and SQLite decision audit trail.
- **NFR-004 (Deployability)**: 100% Vercel-compatible (FastAPI serverless + static HTML/JS/CSS frontend).

## Success Metrics
- **Net Rupee Value**: System must exceed both "Fight Everything" and "Fight Nothing" baselines on held-out test data.
- **Reason-Code Accuracy**: $\ge 80\%$ top-1 accuracy across 10 Visa/Mastercard reason codes.
- **Win Predictor AUC**: Dedicated win model AUC $\ge 0.75$.
