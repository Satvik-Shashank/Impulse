"""Streamlit dashboard for the Chargeback Evidence Auto-Responder.

Tab order is deliberate: the three-way comparison chart is the single most
persuasive artifact in this project and is shown before anything else.

Run:
    streamlit run app.py
"""

import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Chargeback Auto-Responder", layout="wide")

RESULTS_DIR = "results"
MODEL_PATH = "models/classifier.pkl"


@st.cache_resource
def get_responder():
    from src.pipeline.run import ChargebackResponder
    return ChargebackResponder(MODEL_PATH)


@st.cache_data
def load_metrics():
    path = os.path.join(RESULTS_DIR, "metrics.json")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


@st.cache_data
def load_predictions():
    path = os.path.join(RESULTS_DIR, "predictions.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


metrics = load_metrics()

st.title("Chargeback Evidence Auto-Responder")
st.caption("Defense-only representment pipeline — Razorpay AI Buildathon, Track 02: AI Risk Manager")

# ── HEADLINE: three-way comparison, front and center, before any tabs ──
if metrics:
    st.subheader("The bottom line")
    col1, col2, col3 = st.columns(3)
    baselines = metrics["baselines_inr"]
    col1.metric("Fight everything (naive)", f"₹{baselines['fight_everything_net_value']:,.0f}")
    col2.metric("Fight nothing (concede all)", f"₹{baselines['fight_nothing_net_value']:,.0f}")
    col3.metric("This system (cost-optimal)", f"₹{baselines['system_best_net_value']:,.0f}",
                delta=f"₹{baselines['system_best_net_value'] - baselines['fight_everything_net_value']:,.0f} vs naive")

    chart_path = os.path.join(RESULTS_DIR, "three_way_comparison.png")
    if os.path.exists(chart_path):
        st.image(chart_path, use_container_width=True)

    scale = metrics.get("illustrative_scale_extrapolation_inr", {})
    if scale:
        st.caption(
            f"⚠️ {scale.get('note', '')} "
            f"Illustration at 100k disputes/year: ₹{scale.get('at_100k_disputes_per_year', 0):,.0f}."
        )

    st.divider()
else:
    st.warning("No results found. Run `python -m src.evaluate` first to generate metrics.")

# ── Sidebar: Live Demo ──
st.sidebar.header("Live Demo")
uploaded = st.sidebar.file_uploader("Upload dispute JSON", type=["json"])
if uploaded:
    dispute = json.load(uploaded)
    responder = get_responder()
    result = responder.process(dispute)
    st.sidebar.json(result["classification"])
    action_color = "🟢" if result["response"]["action"] == "AUTO_SUBMIT" else "🟡"
    st.sidebar.metric("Action", f"{action_color} {result['response']['action']}")
    st.sidebar.metric("Confidence", f"{result['classification']['confidence']:.1%}")
    with st.sidebar.expander("Full response text"):
        st.text(result["response"]["response_text"])

# ── Main tabs ──
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Classifier Metrics", "💰 Cost Analysis", "🔍 Case Explorer",
    "⚠️ Failure Modes", "🛡️ Guardrails",
])

with tab1:
    st.subheader("Classification Performance (Held-Out Test Set)")
    if metrics:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Accuracy", f"{metrics['reason_code_accuracy']:.1%}")
        c2.metric("Macro Precision", f"{metrics['macro_precision']:.1%}")
        c3.metric("Macro Recall", f"{metrics['macro_recall']:.1%}")
        c4.metric("Win-Prediction AUC", f"{metrics['win_prediction_auc']:.3f}")

        cm_path = os.path.join(RESULTS_DIR, "confusion_matrix.png")
        cal_path = os.path.join(RESULTS_DIR, "calibration_curve.png")
        col_a, col_b = st.columns(2)
        if os.path.exists(cm_path):
            col_a.image(cm_path, caption="Confusion matrix", use_container_width=True)
        if os.path.exists(cal_path):
            col_b.image(cal_path, caption="Calibration curve", use_container_width=True)

        st.subheader("Per-class precision / recall / F1")
        per_class_df = pd.DataFrame(metrics["per_class"]).T
        st.dataframe(per_class_df)
    else:
        st.info("Run evaluation first.")

with tab2:
    st.subheader("Cost-Sensitive Operating Point Selection")
    if metrics:
        threshold_options = [c["threshold"] for c in metrics["cost_curve"]]
        chosen = st.select_slider("Confidence threshold", options=threshold_options,
                                   value=metrics["best_operating_point"]["threshold"])
        chosen_row = next(c for c in metrics["cost_curve"] if c["threshold"] == chosen)
        c1, c2, c3 = st.columns(3)
        c1.metric("Auto-respond %", f"{chosen_row['auto_respond_pct']:.1%}")
        c2.metric("Win rate at threshold", f"{chosen_row['win_rate_at_threshold']:.1%}")
        c3.metric("Net ₹ / dispute", f"₹{chosen_row['net_value_per_dispute']:.0f}")

        curve_path = os.path.join(RESULTS_DIR, "cost_threshold_curve.png")
        if os.path.exists(curve_path):
            st.image(curve_path, use_container_width=True)

        st.caption("Cost figures are working modeling assumptions, not cited industry data.")
    else:
        st.info("Run evaluation first.")

with tab3:
    st.subheader("Individual Case Inspector")
    preds = load_predictions()
    if preds is not None:
        selected_id = st.selectbox("Dispute ID", preds["dispute_id"].tolist())
        row = preds[preds["dispute_id"] == selected_id].iloc[0]
        st.json(row.to_dict())
    else:
        st.info("Run evaluation first to populate case data.")

with tab4:
    st.subheader("Documented Failure Modes")
    st.markdown("""
The system is deliberately tested against cases it is expected to handle
poorly, and its behavior in each case is documented rather than hidden.

| Failure mode | What happens | Why this is the right behavior |
|---|---|---|
| **Weak/absent evidence** | Routed to `HUMAN_REVIEW`, never auto-submitted | Auto-submit requires both a confidence threshold *and* a minimum evidence strength — a confident-but-unsupported classification cannot bypass this. |
| **Ambiguous mixed-signal dispute** (some fraud indicators, some legitimate-use indicators) | Calibration keeps confidence appropriately low, which routes it to human review rather than a confident wrong answer | Platt scaling is what makes "low confidence" mean something real, rather than an arbitrary number. |
| **Unknown/malformed reason code** | Falls back to `generic.j2` template, `auto_respond_eligible = False` | The system fails closed, not open, on unrecognized input. |
| **High-value dispute with strong evidence** | Still subject to the same threshold logic as any other case — no special-casing by amount | Prevents a failure mode where the system is more permissive exactly when the financial stakes are highest. |

See `tests/test_failure_modes.py` for the executable versions of these cases.
""")

with tab5:
    st.subheader("Defense-Only Guardrails")
    st.markdown("""
| Guardrail | Implementation |
|---|---|
| No dispute generation | System can only respond to incoming disputes, never initiate them |
| No PII | 100% synthetic data (Faker) — no real customer or transaction data |
| No raw card data | Card fields are masked/tokenized; only match/no-match booleans are used |
| Auditable evidence logic | Evidence-to-reason-code mapping is an explicit rule table, not a learned black box |
| Full audit trail | Every decision is logged: classification, evidence used, confidence, action taken |
| Kill switch | `AUTO_RESPOND_CONFIDENCE` in `src/pipeline/response_generator.py` — set to `1.0` to force 100% human review |
""")
