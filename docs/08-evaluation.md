# Phase 8 — Model Evaluation & Metrics Report

## Summary Metrics (Held-Out Test Split, N=750)

| Metric | Measured Value | Target | Status |
|---|---|---|---|
| Reason-Code Accuracy | 98.4% | $\ge 80.0\%$ | PASSED |
| Macro Precision | 98.7% | $\ge 75.0\%$ | PASSED |
| Macro Recall | 98.4% | $\ge 75.0\%$ | PASSED |
| Macro F1-Score | 98.5% | $\ge 75.0\%$ | PASSED |
| Win Prediction AUC (Evidence) | 0.654 | Informational | Measured |
| Dedicated Win Predictor AUC | 0.7537 | $\ge 0.750$ | PASSED |

## Three-Way Baseline Comparison (Rupee Net Value)
- **Fight Everything (Naive)**: ₹520,200
- **Fight Nothing (Concede All)**: -₹153,300
- **This System (Cost-Optimal Gate @ 0.50)**: ₹850,500
- **Net Delta vs Naive**: +₹330,300 (+63.5% improvement)

These figures are measured on the regenerated synthetic test split. They are not evidence of equivalent performance on an unseen merchant dataset.

## Artifacts Generated
- `results/metrics.json`: Full classification and cost curve evaluation statistics.
- `results/confusion_matrix.png`: Multi-class confusion matrix across 10 reason codes.
- `results/calibration_curve.png`: Platt calibration curve verifying confidence reliability.
- `results/cost_threshold_curve.png`: Cost-sensitive operating point selection graph.
- `results/three_way_comparison.png`: Executive headline comparison chart.
