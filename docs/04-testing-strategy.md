# Phase 4 — Testing & Validation Strategy

## Test Architecture
The test suite spans unit tests, integration tests, pipeline validation, and edge-case failure mode testing using `pytest`.

```
tests/
├── conftest.py               # Shared fixtures (trained classifier, synthetic datasets)
├── test_classifier.py        # Reason-code classifier output shape, batching, baseline check
├── test_win_predictor.py     # WinPredictor probabilities, batching, feature importances
├── test_evidence.py          # Evidence retriever rule-table compliance
├── test_failure_modes.py     # Edge cases, weak evidence, invalid codes, kill switch
├── test_pipeline.py          # End-to-end ChargebackResponder pipeline integration
└── test_api.py               # FastAPI serverless endpoints integration tests
```

## Test Suite Execution
Run tests locally via `.venv`:
```bash
.venv\Scripts\pytest
```

## Categories of Tests
1. **Classifier Baseline Guard Test**: Validates that reason-code classification accuracy significantly outperforms a uniform random baseline ($> 1.5 \times \text{random}$).
2. **Win Predictor Range Test**: Ensures all output win probabilities fall strictly within $[0.0, 1.0]$.
3. **Failure Mode Handling**:
   - Weak/missing evidence correctly routes to `HUMAN_REVIEW`.
   - Low confidence ($< 0.70$) correctly routes to `HUMAN_REVIEW`.
   - Unknown reason codes fall back safely to `generic.j2` template with `auto_respond_eligible = False`.
   - Setting `AUTO_RESPOND_CONFIDENCE = 1.0` acts as a functioning kill switch forcing 100% human review.
4. **API Integration Tests**: Verifies HTTP status codes, response schemas, error handling, and database interaction across `/api/disputes`, `/api/health`, `/api/dashboard/summary`, and `/api/monitoring/drift`.
