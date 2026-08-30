# Chargeback Evidence Auto-Responder

Defense-only ML pipeline for the **Razorpay AI Buildathon — Track 02: AI Risk Manager**.

## The bottom line

On the held-out test set, this system's cost-optimal decision policy recovers
more net value than either naive strategy — fighting every dispute or
conceding every dispute. See `results/three_way_comparison.png` and
`results/metrics.json` → `baselines_inr` after running the evaluation step
below; the exact numbers depend on your generated dataset seed and are
reported honestly, not asserted in advance here.

## What it does

Given an incoming chargeback dispute, the system:

1. **Classifies** the dispute reason code (LightGBM, multi-class, Platt-calibrated,
   trained on features that are genuinely predictive of reason code — see
   `src/data/generate_disputes.py` for how the synthetic data is constructed
   to make this a real learnable problem rather than a guess).

2. **Retrieves & scores** the evidence required by that reason code, using an
   explicit, auditable rule table derived from published card-network
   representment specifications — deliberately not a learned/black-box step,
   because a financial decision system should be inspectable at this layer.

3. **Drafts** a network-compliant representment response (Jinja2 templates).

4. Decides **AUTO_SUBMIT vs HUMAN_REVIEW** using a calibrated confidence
   threshold combined with a minimum evidence-strength gate.

It ships with an honest, **cost-sensitive evaluation** (rupee-denominated
FP/FN/TP accounting, a threshold-vs-value curve, and a three-way baseline
comparison), plus a **documented set of failure modes** — ambiguous
mixed-signal disputes, malformed reason codes, missing fields, and high-value
disputes are all explicitly tested and their behavior is described, not
hidden.

## Guardrails (defense-only)

- Can only **respond** to disputes, never initiate them.
- **100% synthetic data** (Faker) — no PII, no real card numbers.
- Every response carries a full reasoning chain for audit.
- **Kill switch**: set `AUTO_RESPOND_CONFIDENCE = 1.0` in
  `src/pipeline/response_generator.py` to disable all auto-responses.

## Setup

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    # macOS + Apple Silicon: brew install libomp   (LightGBM OpenMP runtime)

## Run the full flow

    python -m src.data.generate_disputes
    python -m src.train
    python -m src.evaluate --test-set data/disputes_test.csv --output results/
    python -m src.pipeline.run sample_dispute.json
    python -m src.pipeline.run sample_dispute_weak_evidence.json   # HUMAN_REVIEW path
    streamlit run app.py

## Tests

    pytest -q

`tests/test_classifier.py::test_classifier_beats_random_baseline` is a
regression guard: it fails loudly if the synthetic data generator is ever
changed in a way that decouples `reason_code` from the transaction features
again, which would silently make the accuracy numbers meaningless.

## A note on the numbers

All ₹ cost/savings figures (`COST_FP`, `COST_FN`, `SAVINGS_TP` in
`src/evaluate.py`) are working modeling assumptions used to illustrate the
cost-sensitive decision framework, not cited industry statistics. State this
explicitly whenever these figures are shown. The same applies to the
"illustrative scale extrapolation" block in `metrics.json` — it extrapolates
this system's own measured per-dispute value across hypothetical volumes and
is not a Razorpay-reported figure.
