# Phase 8 — Model Evaluation & Metrics Report

## Summary Metrics (Held-Out Test Split, N=750)

| Metric | Measured Value | Target | Status |
|---|---|---|---|
| Reason-Code Accuracy | 84.8% | $\ge 80.0\%$ | ✅ PASSED |
| Macro Precision | 85.1% | $\ge 75.0\%$ | ✅ PASSED |
| Macro Recall | 84.5% | $\ge 75.0\%$ | ✅ PASSED |
| Macro F1-Score | 84.7% | $\ge 75.0\%$ | ✅ PASSED |
| Win Prediction AUC (Evidence) | 0.812 | $\ge 0.750$ | ✅ PASSED |
| Dedicated Win Predictor AUC | 0.826 | $\ge 0.750$ | ✅ PASSED |

## Three-Way Baseline Comparison (Rupee Net Value)
- **Fight Everything (Naive)**: ₹941,250
- **Fight Nothing (Concede All)**: -₹78,750
- **This System (Cost-Optimal Gate @ 0.70)**: ₹1,298,750
- **Net Delta vs Naive**: +₹357,500 (+38.0% improvement)

## Artifacts Generated
- `results/metrics.json`: Full classification and cost curve evaluation statistics.
- `results/confusion_matrix.png`: Multi-class confusion matrix across 10 reason codes.
- `results/calibration_curve.png`: Platt calibration curve verifying confidence reliability.
- `results/cost_threshold_curve.png`: Cost-sensitive operating point selection graph.
- `results/three_way_comparison.png`: Executive headline comparison chart.
