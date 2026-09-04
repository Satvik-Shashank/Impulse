#  Impulse
### Chargeback Intelligence & Auto-Resolution Platform

**Classify. Verify. Decide. Recover.** — a defense-only, cost-aware chargeback response system built for the Razorpay AI Buildathon, Track 02: AI Risk Manager.

[![Track](https://img.shields.io/badge/Razorpay%20Buildathon-Track%2002%3A%20AI%20Risk%20Manager-1B2A4E)]()
[![Tests](https://img.shields.io/badge/tests-32%2F32%20passing-16a34a)]()
[![Reason Code Accuracy](https://img.shields.io/badge/reason--code%20accuracy-98.4%25-16a34a)]()
[![Win Predictor AUC](https://img.shields.io/badge/win--predictor%20AUC-0.7537-2563eb)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## What this is

When a customer disputes a card transaction, merchants have a narrow window to submit proof the charge was legitimate — different reason codes require completely different evidence, and a wrong or late response means an automatic loss, even when the merchant was in the right.

**Impulse** takes an incoming dispute and, in under a second, tells you: *what kind of dispute this is, what evidence you actually have for it, how likely you are to win it, and whether fighting it is worth the money* — with every recommendation backed by a rupee-denominated cost calculation, not just a confidence score.

> Most chargebacks are contestable. Most are lost to slow, manual evidence assembly — not because the merchant was wrong. Impulse automates the part that's actually solvable.

---

## The pipeline

```
Incoming Dispute
      │
      ▼
Reason Code Classifier ──────► predicts which of 10 dispute types applies
      │                        (LightGBM, 98.4% accuracy, calibrated confidence)
      ▼
Evidence Retriever ───────────► checks required proof against what's on file
      │                        (deterministic rule table, fully auditable)
      ▼
Win Predictor ────────────────► estimates P(merchant wins if we fight)
      │                        (dedicated LightGBM model, 0.75 AUC)
      ▼
Decision Engine ──────────────► expected-value calculation in ₹, not just %
      │
   ┌──┴──┐
   ▼     ▼
AUTO    HUMAN
RESPOND REVIEW
```

Two models, kept deliberately separate — "what is this dispute" and "will we win it" are different questions, and conflating them makes both harder to trust and debug independently.

---

## Why this, and not just an accuracy leaderboard entry

The track's own bar was explicit: **"honest metrics including false-positive cost."** Most of what this project demonstrates is built around answering that literally, not decoratively:

- Every headline metric is reported with a **95% bootstrap confidence interval**, not a bare point estimate.
- Where an internal metric didn't clear our own documented target (an early evidence-heuristic AUC of 0.654 vs. a ≥0.75 bar), it's labeled **"Informational / Measured"** in the docs rather than marked as passed — and a properly dedicated model was built and validated separately until it genuinely cleared the bar (0.7537).
- A **fairness audit** checks accuracy across product categories and transaction-amount deciles, specifically looking for blind spots rather than assuming uniform performance.
- The system has an explicit, tested **kill switch** — set a config value to force 100% human review, no exceptions — and a documented set of **failure modes**, each backed by an executable test that proves the system degrades safely rather than guessing confidently.

---

## Bring Your Own Data

Sample synthetic data is provided out of the box, but the pipeline isn't hardwired to it. Upload your own transaction/dispute spreadsheet (`.xlsx`/`.csv`) and the system will:

1. Auto-suggest a column mapping to the fields it needs
2. Show a validation report — exactly how many rows are usable and why any were dropped
3. Strip every column that isn't part of the required schema before anything is processed (proven by an automated test that uploads a file with a PII column and asserts it's discarded)
4. Run the full pipeline on your real data, in-memory only, with a session TTL — nothing is written to permanent storage

> Uploading real data proves the *pipeline* generalizes beyond the sample set. It does not, on its own, prove the model's accuracy holds on your data — that requires a labeled test set of your own outcomes, which this feature makes possible but doesn't fabricate for you.

---

## Model summary

| | Reason Code Classifier | Win Predictor |
|---|---|---|
| **Task** | Multi-class (10 reason codes) | Binary (will merchant win?) |
| **Algorithm** | LightGBM + Platt calibration | LightGBM + Platt calibration |
| **Test accuracy / AUC** | **98.4%** (95% CI: 97.5–99.2%) | **0.7537 AUC** |
| **Macro F1** | 98.49% | — |
| **Held-out test size** | 750 disputes | 750 disputes |
| **Fallback behavior** | Explicit `model_status` flag; auto-submit structurally blocked if fallback active | Returns `0.5` (unknown) on failure — never fabricates a confident score |

Full per-class metrics, the fairness audit, and the cost-curve breakdown are in [`docs/08-evaluation.md`](docs/08-evaluation.md) and `results/metrics.json`.

---

## Measured business impact (held-out test set, n=750)

| Strategy | Net value |
|---|---|
| Fight every dispute (naive) | ₹5,20,200 |
| Fight no disputes (concede all) | −₹1,53,300 |
| **Impulse (cost-optimal threshold)** | **₹8,50,500** |

*Cost assumptions (₹1,000 cost of a losing auto-fight, ₹2,250 value of a won auto-response) are working modeling assumptions used to demonstrate cost-sensitive decision-making — not cited industry data. Stated explicitly wherever these figures appear.*

---

## Quickstart

```bash
git clone https://github.com/Satvik-Shashank/Impulse.git
cd Impulse
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# macOS + Apple Silicon: brew install libomp

python -m src.data.generate_disputes     # regenerate synthetic dataset
python -m src.train                       # train the reason-code classifier
python -m src.evaluate --test-set data/disputes_test.csv --output results/

uvicorn api.index:app --reload            # run the API locally
# open public/index.html, or deploy — see vercel.json
```

Run the tests:
```bash
pytest -q     # 32/32 passing
```

---

## Guardrails

| Guardrail | How it's enforced |
|---|---|
| Defense-only | The system can only respond to a dispute that already exists — no code path creates or simulates one |
| No PII | 100% synthetic sample data; uploaded data is stripped to the schema allow-list and never persisted |
| Auditable evidence logic | Evidence-to-reason-code mapping is an explicit rule table, not a learned black box |
| Kill switch | A single config value forces 100% human review — tested, not just documented |
| Fails closed | Model load or inference failure routes to human review, never to a confident guess |
| Full audit trail | Every decision — classification, evidence used, confidence, action — is logged |

---

## Project structure

```
Impulse/
├── api/                  FastAPI app (serverless entry point)
├── src/
│   ├── data/              synthetic dataset generator
│   ├── models/             reason-code classifier + win predictor
│   ├── pipeline/           evidence retriever, response generator, orchestration
│   ├── db/                 persistence layer
│   ├── evaluate.py         held-out evaluation, cost curves, fairness audit
│   └── train.py
├── public/                frontend dashboard
├── docs/                  product spec, architecture, evaluation, ADRs
├── tests/                 32 tests — pipeline, API, BYOD, guardrails, failure modes
└── results/                metrics.json, charts, monitoring log
```

---

## What this is, and isn't

**Is:** a rigorously tested prototype, validated with bootstrap confidence intervals and a fairness audit, with an explicit kill switch and documented failure modes — built to be honest about what it can prove and what it can't.

**Isn't:** a claim of production readiness. All model results are measured on synthetic data designed to have realistic, learnable patterns — not a guarantee of equivalent performance on a real merchant's live data. Where our own numbers didn't clear our own bar, we said so instead of hiding it.

---

## License

MIT — see [`LICENSE`](LICENSE).
