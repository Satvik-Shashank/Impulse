# Changelog

## [2.0.0] - 2026-08-31
### Added
- Dedicated LightGBM `WinPredictor` model with Platt-scaled calibration (`src/models/win_predictor.py`).
- Top-k candidate reason-code prediction in `DisputeClassifier`.
- Thread-safe `DisputeStore` wrapper around SQLAlchemy models (`src/api/storage.py`).
- Append-only prediction log and rolling drift monitor (`src/api/monitoring.py`).
- Comprehensive REST API endpoints (`/api/disputes`, `/api/dashboard/summary`, `/api/monitoring/drift`).
- Premium dark-mode glassmorphism dashboard in static HTML/JS/CSS (`public/`).
- Full 6-phase engineering documentation package in `docs/`.
- Additional unit and integration test suites (`test_win_predictor.py`, `test_api.py`).

### Changed
- Refactored pipeline to output expected value in INR and human-readable reasoning chain.
- Updated `vercel.json` and API entry point `api/index.py`.

### Removed
- Removed Streamlit entirely in favor of static HTML/JS/CSS + Vercel Serverless.
