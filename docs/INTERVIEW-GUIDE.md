# Interview & Technical Review Guide

This guide prepares the developer to explain every major architectural decision during technical evaluations.

## Key Talking Points

### Q1: Why build a custom decision system instead of using LLMs directly?
> "Chargeback representment is governed by strict, published card network specs (Visa/Mastercard). LLMs can hallucinate evidence rules or output uncalibrated confidence. We use machine learning where it excels—predicting reason codes and win probabilities from tabular transaction signals—and deterministic rule tables for evidence requirements. This makes the system 100% auditable and compliant."

### Q2: How do you justify the auto-respond threshold?
> "We perform cost-sensitive operating point selection. We model the financial impact of False Positives (₹1,000 lost fee + case), False Negatives (₹350 ops labor), and True Positives (₹2,250 net savings). By calibrating our models with Platt scaling, our confidence scores represent real probabilities, enabling us to mathematically maximize net Rupee recovery."

### Q3: Why is Streamlit avoided in favor of Vercel Static + FastAPI?
> "Streamlit is useful for quick prototypes, but it introduces heavy server overhead and state synchronization issues. Tailoring for Vercel deployment with static HTML/JS/CSS frontend and FastAPI serverless backend yields sub-50ms latency, zero cold-start delay, and production-grade stability."

### Q4: How is model drift monitored?
> "Our monitoring layer logs every prediction to an append-only JSONL file and computes rolling statistics over sliding windows (confidence mean/std, evidence availability, reason-code distributions). This provides early warning when incoming dispute characteristics diverge from training priors."
