# Phase 10 — Design Decisions & Trade-Offs

## Major Technical Decisions

### 1. Separate Reason Classifier and Win Predictor Models
- **Decision**: Train two distinct models — `DisputeClassifier` for multi-class reason-code classification and `WinPredictor` for binary outcome prediction.
- **Rationale**: Conflating "what type of dispute is this?" with "will we win it?" into a single model makes both harder to calibrate and debug independently.

### 2. Platt-Scaled Calibration
- **Decision**: Wrap LightGBM models in scikit-learn's `CalibratedClassifierCV` using the sigmoid method.
- **Rationale**: Raw tree probabilities tend to push towards 0 and 1. Platt scaling ensures predicted confidence maps directly to true empirical accuracy, which is required for reliable cost-threshold gating.

### 3. Rule-Based Evidence Retrieval
- **Decision**: Use a deterministic rule table for mapping reason codes to evidence requirements rather than an ML model.
- **Rationale**: Visa and Mastercard representment guidelines are fixed, published specs. A black-box learned retriever would be un-auditable and non-compliant with card network specs.

### 4. Vercel Static HTML/JS/CSS Frontend
- **Decision**: Avoid Streamlit entirely in favor of static HTML/JS/CSS served directly by Vercel.
- **Rationale**: Streamlit requires an active Python server process, whereas static assets deploy natively to Vercel's CDN with zero cold-start delay and optimal response speed.
