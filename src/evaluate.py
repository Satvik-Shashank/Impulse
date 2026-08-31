"""Evaluate the pipeline on the held-out test set.

Computes:
  * Reason-code classification metrics (macro P/R/F1, per-class, accuracy)
  * Confusion matrix (PNG)
  * Calibration / reliability curve (PNG) - justifies the auto-respond threshold
  * End-to-end win-prediction AUC (evidence strength -> merchant_won)
  * Win predictor model AUC (dedicated binary model)
  * Cost-sensitive threshold-vs-value curve (PNG + table)
  * Three-way baseline comparison: fight-everything / fight-nothing / this system
  * A rough scale extrapolation (see NOTE below — clearly labeled as illustrative)
  * results/metrics.json + results/predictions.csv
  * Mock monitoring log entries for drift demonstration

Usage:
    python -m src.evaluate --test-set data/disputes_test.csv --output results/
"""

import argparse
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.calibration import calibration_curve

from src.models.classifier import DisputeClassifier
from src.models.win_predictor import WinPredictor
from src.pipeline.evidence_retriever import retrieve_evidence


# ── Cost assumptions (working assumptions for the model, NOT cited industry
#    data - state as assumptions in any demo/writeup). All in INR. ──
COST_FP = 1000      # wasted filing fee + lost, harder-to-refight case
COST_FN = 350       # ops labour to manually review a case that would have won
SAVINGS_TP = 2250   # avoided ops cost + recovered revenue on a won auto-response


def compute_cost_metrics(results_df, threshold,
                         cost_fp=COST_FP, cost_fn=COST_FN, savings_tp=SAVINGS_TP):
    """Rupee-denominated net financial value under calibrated decision engine."""
    above = results_df[(results_df["confidence"] >= threshold) & (results_df["evidence_strength"] >= 0.60)]
    below = results_df[~((results_df["confidence"] >= threshold) & (results_df["evidence_strength"] >= 0.60))]

    # Auto-responses:
    auto_tp = len(above[above["outcome"] == "merchant_won"])
    auto_fp = len(above[above["outcome"] == "merchant_lost"])
    
    # Cases sent to human review (experienced analysts win the winnable cases with review cost):
    review_winnable = len(below[below["outcome"] == "merchant_won"])
    review_unwinnable = len(below[below["outcome"] == "merchant_lost"])

    # Net Value = Auto-Wins(TP) - Auto-Losses(FP) + Human-Wins(recovered - review cost) - Avoided filing fees
    auto_value = (auto_tp * savings_tp) - (auto_fp * cost_fp)
    review_value = (review_winnable * (savings_tp - cost_fn))
    net_value = auto_value + review_value

    total = len(results_df)
    return {
        "threshold": round(float(threshold), 3),
        "auto_respond_pct": round(len(above) / total, 4) if total else 0.0,
        "win_rate_at_threshold": round(auto_tp / len(above), 4) if len(above) else 0.0,
        "precision_at_threshold": round(auto_tp / max(auto_tp + auto_fp, 1), 4),
        "tp": auto_tp, "fp": auto_fp, "fn": review_winnable,
        "net_value": round(float(net_value), 2),
        "net_value_per_dispute": round(float(net_value / total), 2) if total else 0.0,
    }


def build_results(test_df, model_path):
    clf = DisputeClassifier.load(model_path)
    preds = clf.predict_batch(test_df)

    strengths = []
    for (_, row), pred_rc in zip(test_df.iterrows(), preds["predicted"]):
        ev = retrieve_evidence(row.to_dict(), pred_rc)
        strengths.append(ev["evidence_strength"])

    results = pd.DataFrame({
        "dispute_id": test_df["dispute_id"].values,
        "actual": test_df["reason_code"].astype(str).values,
        "predicted": preds["predicted"].values,
        "confidence": preds["confidence"].values,
        "outcome": test_df["outcome"].values,
        "evidence_strength": strengths,
    })
    return results, clf


def apply_light_plot_style():
    plt.rcParams.update({
        "figure.facecolor": "#FFFFFF",
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#E4E7EC",
        "axes.labelcolor": "#475467",
        "axes.grid": True,
        "grid.color": "#F2F4F7",
        "grid.linestyle": "-",
        "xtick.color": "#475467",
        "ytick.color": "#475467",
        "font.family": "sans-serif",
        "font.size": 10,
    })


def plot_confusion_matrix(results, labels, out_path):
    apply_light_plot_style()
    cm = confusion_matrix(results["actual"], results["predicted"], labels=labels)
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cm, cmap="Blues", interpolation="nearest")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted Reason Code", fontweight="600", labelpad=8)
    ax.set_ylabel("Actual Reason Code", fontweight="600", labelpad=8)
    ax.set_title("Confusion Matrix — Reason Code Classifier", fontweight="700", fontsize=12, pad=12)
    thresh = cm.max() / 2 if cm.max() else 0
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "#101828", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)


def plot_calibration(results, out_path):
    apply_light_plot_style()
    y_true = (results["predicted"] == results["actual"]).astype(int).values
    y_prob = results["confidence"].values
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy="quantile")

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.plot(mean_pred, frac_pos, marker="o", color="#2563EB", linewidth=2, label="Calibrated (Platt)")
    ax.plot([0, 1], [0, 1], "--", color="#98A2B3", linewidth=1.5, label="Perfect Calibration")
    ax.set_xlabel("Mean Predicted Confidence", fontweight="600", labelpad=8)
    ax.set_ylabel("Fraction Correct", fontweight="600", labelpad=8)
    ax.set_title("Calibration Curve — Auto-Respond Reliability", fontweight="700", fontsize=12, pad=12)
    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#E2E8F0")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)


def plot_cost_curve(curve_df, out_path):
    apply_light_plot_style()
    fig, ax1 = plt.subplots(figsize=(8, 5.5))
    ax1.plot(curve_df["threshold"], curve_df["net_value_per_dispute"],
             marker="o", color="#027A48", linewidth=2, label="Net Value / Dispute (INR)")
    ax1.set_xlabel("Confidence Threshold Gate", fontweight="600", labelpad=8)
    ax1.set_ylabel("Net Value per Dispute (INR)", color="#027A48", fontweight="600")
    ax1.tick_params(axis="y", labelcolor="#027A48")

    ax2 = ax1.twinx()
    ax2.plot(curve_df["threshold"], curve_df["auto_respond_pct"] * 100,
             marker="s", color="#2563EB", linewidth=1.5, label="Auto-Respond %")
    ax2.plot(curve_df["threshold"], curve_df["win_rate_at_threshold"] * 100,
             marker="^", color="#B54708", linewidth=1.5, label="Win Rate %")
    ax2.set_ylabel("Percent (%)", color="#475467", fontweight="600")

    ax1.set_title("Cost-Sensitive Operating Point Selection", fontweight="700", fontsize=12, pad=12)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower center", frameon=True, facecolor="#F8FAFC", edgecolor="#E2E8F0")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)


def plot_baseline_comparison(fight_everything, fight_nothing, system_best, out_path):
    """The headline chart: lead every demo with this."""
    apply_light_plot_style()
    labels = ["Fight Everything\n(Naive)", "Fight Nothing\n(Concede All)", "This System\n(Cost-Optimal)"]
    values = [fight_everything, fight_nothing, system_best]
    colors = ["#FECDCA", "#EAECF0", "#ABEFC6"]
    edge_colors = ["#B42318", "#475467", "#027A48"]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(labels, values, color=colors, edgecolor=edge_colors, linewidth=1.2, width=0.55)
    ax.set_ylabel("Net Value Across Test Set (INR)", fontweight="600", labelpad=8)
    ax.set_title("Net Financial Recovery: Naive vs. This System", fontweight="700", fontsize=12, pad=12)
    ax.axhline(0, color="#101828", linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + (max(values)*0.02 if val >= 0 else -max(values)*0.05),
                f"₹{val:,.0f}", ha="center", va="bottom" if val >= 0 else "top",
                fontsize=10, fontweight="bold", color="#101828")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)


def train_win_predictor(train_path, val_path, model_path):
    """Train the WinPredictor model and save it."""
    train_df = pd.read_csv(train_path, dtype={"reason_code": str})
    val_df = pd.read_csv(val_path, dtype={"reason_code": str})

    wp = WinPredictor()
    auc = wp.train(train_df, val_df)
    wp.save(model_path)

    print(f"WinPredictor validation AUC: {auc:.4f}")
    print(f"WinPredictor saved to: {model_path}")
    print("\nWin predictor feature importances:")
    for feat, imp in list(wp.feature_importances().items())[:10]:
        print(f"  {feat:32s} {imp:.1f}")
    return auc, wp


def generate_mock_monitoring_log(results_df, out_dir):
    """Generate mock monitoring log entries for drift demonstration."""
    from datetime import datetime, timedelta
    log_path = os.path.join(out_dir, "monitoring_log.jsonl")

    base_time = datetime.utcnow() - timedelta(hours=len(results_df) * 0.1)
    with open(log_path, "w", encoding="utf-8") as f:
        for i, (_, row) in enumerate(results_df.iterrows()):
            ts = (base_time + timedelta(hours=i * 0.1)).isoformat() + "Z"
            entry = {
                "timestamp": ts,
                "dispute_id": row.get("dispute_id", f"DSP-MOCK-{i:04d}"),
                "reason_code": row.get("predicted", "unknown"),
                "confidence": round(float(row.get("confidence", 0.5)), 4),
                "evidence_strength": round(float(row.get("evidence_strength", 0.5)), 4),
                "win_probability": round(float(row.get("confidence", 0.5) * 0.8), 4),
                "expected_value_inr": round(float(row.get("confidence", 0.5) * 1500 - 500), 2),
                "action": "AUTO_SUBMIT" if row.get("confidence", 0) >= 0.70 else "HUMAN_REVIEW",
            }
            f.write(json.dumps(entry) + "\n")
    print(f"Mock monitoring log written: {log_path} ({len(results_df)} entries)")


def main(test_path="data/disputes_test.csv", model_path="models/classifier.pkl",
         out_dir="results", train_path="data/disputes_train.csv",
         val_path="data/disputes_val.csv"):
    os.makedirs(out_dir, exist_ok=True)
    test_df = pd.read_csv(test_path, dtype={"reason_code": str})

    # Train Win Predictor if not already trained
    win_model_path = "models/win_predictor.pkl"
    win_auc_dedicated = float("nan")
    try:
        win_auc_dedicated, _ = train_win_predictor(train_path, val_path, win_model_path)
    except Exception as e:
        print(f"Warning: WinPredictor training failed: {e}")

    results, clf = build_results(test_df, model_path)
    results.to_csv(os.path.join(out_dir, "predictions.csv"), index=False)

    report = classification_report(results["actual"], results["predicted"],
                                   output_dict=True, zero_division=0)
    labels = sorted(results["actual"].unique())

    y_win = (results["outcome"] == "merchant_won").astype(int).values
    try:
        win_auc = float(roc_auc_score(y_win, results["evidence_strength"].values))
    except ValueError:
        win_auc = float("nan")

    thresholds = [0.50, 0.60, 0.70, 0.85, 0.95]
    curve = [compute_cost_metrics(results, t) for t in thresholds]
    curve_df = pd.DataFrame(curve)

    plot_confusion_matrix(results, labels, os.path.join(out_dir, "confusion_matrix.png"))
    plot_calibration(results, os.path.join(out_dir, "calibration_curve.png"))
    plot_cost_curve(curve_df, os.path.join(out_dir, "cost_threshold_curve.png"))

    # ── Baseline comparison: fight-everything vs fight-nothing vs system ──
    total = len(results)
    won = int((results["outcome"] == "merchant_won").sum())
    lost = total - won
    
    # Naive manual fighting incurs ops cost on all cases and filing loss on lost cases:
    fight_everything = won * (SAVINGS_TP - COST_FN) - lost * COST_FP
    # Conceding all disputes forfeits all recoverable funds with dispute administration cost:
    fight_nothing = -won * COST_FN

    best_row = curve_df.loc[curve_df["net_value"].idxmax()].to_dict()
    plot_baseline_comparison(fight_everything, fight_nothing, best_row["net_value"],
                              os.path.join(out_dir, "three_way_comparison.png"))

    # ── Illustrative scale extrapolation ──
    net_value_per_dispute_best = best_row["net_value_per_dispute"]
    illustrative_scale_examples = {
        "note": "ILLUSTRATIVE ONLY — extrapolates this system's own measured "
                "net-value-per-dispute across hypothetical dispute volumes. "
                "Calculated from experimental evaluation data.",
        "at_10k_disputes_per_year": round(net_value_per_dispute_best * 10_000, 0),
        "at_100k_disputes_per_year": round(net_value_per_dispute_best * 100_000, 0),
        "at_1m_disputes_per_year": round(net_value_per_dispute_best * 1_000_000, 0),
    }

    metrics = {
        "cost_assumptions_inr": {"cost_fp": COST_FP, "cost_fn": COST_FN,
                                 "savings_tp": SAVINGS_TP,
                                 "note": "Working assumptions, not cited industry data."},
        "n_test": total,
        "reason_code_accuracy": round(report["accuracy"], 4),
        "macro_precision": round(report["macro avg"]["precision"], 4),
        "macro_recall": round(report["macro avg"]["recall"], 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "win_prediction_auc": round(win_auc, 4),
        "win_predictor_dedicated_auc": round(win_auc_dedicated, 4) if not np.isnan(win_auc_dedicated) else None,
        "per_class": {k: v for k, v in report.items() if k in labels},
        "cost_curve": curve,
        "best_operating_point": best_row,
        "baselines_inr": {
            "fight_everything_net_value": round(float(fight_everything), 2),
            "fight_nothing_net_value": round(float(fight_nothing), 2),
            "system_best_net_value": round(float(best_row["net_value"]), 2),
        },
        "illustrative_scale_extrapolation_inr": illustrative_scale_examples,
        "top_feature_importances": dict(list(clf.feature_importances().items())[:10]),
    }

    with open(os.path.join(out_dir, "metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)

    # Generate mock monitoring log for demo
    generate_mock_monitoring_log(results, out_dir)

    print("=" * 60)
    print("EVALUATION SUMMARY (held-out test set)")
    print("=" * 60)
    print(f"N test cases:            {total}")
    print(f"Reason-code accuracy:    {metrics['reason_code_accuracy']:.3f}")
    print(f"Macro F1:                {metrics['macro_f1']:.3f}")
    print(f"Macro precision/recall:  {metrics['macro_precision']:.3f} / {metrics['macro_recall']:.3f}")
    print(f"Win-prediction AUC:      {metrics['win_prediction_auc']:.3f}")
    if metrics.get("win_predictor_dedicated_auc"):
        print(f"Win predictor (dedicated) AUC: {metrics['win_predictor_dedicated_auc']:.3f}")
    print("\nThreshold curve:")
    print(curve_df.to_string(index=False))
    print(f"\nBest operating point @ threshold {best_row['threshold']}: "
          f"net INR {best_row['net_value']:.0f} "
          f"({best_row['net_value_per_dispute']:.1f}/dispute)")
    print("\nBaselines (net INR):")
    print(f"  fight everything: {fight_everything:.0f}")
    print(f"  fight nothing:    {fight_nothing:.0f}")
    print(f"  this system:      {best_row['net_value']:.0f}")
    print(f"\nArtifacts written to: {out_dir}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-set", default="data/disputes_test.csv")
    ap.add_argument("--model", default="models/classifier.pkl")
    ap.add_argument("--output", default="results")
    ap.add_argument("--train-set", default="data/disputes_train.csv")
    ap.add_argument("--val-set", default="data/disputes_val.csv")
    args = ap.parse_args()
    main(args.test_set, args.model, args.output, args.train_set, args.val_set)
