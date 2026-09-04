"""Main pipeline: dispute JSON -> full response package.

Integrates the reason-code classifier, win probability predictor,
evidence retriever, and response generator into a single pipeline.

Usage:
    python -m src.pipeline.run sample_dispute.json
"""

import json
import os
import sys
from src.models.classifier import DisputeClassifier
from src.pipeline.evidence_retriever import retrieve_evidence
from src.pipeline.response_generator import generate_response

# Cost assumptions (working modeling assumptions, not cited industry data)
COST_FP = 1000      # wasted filing fee + lost, harder-to-refight case
COST_FN = 350       # ops labour to manually review a case that would have won
SAVINGS_TP = 2250   # avoided ops cost + recovered revenue on a won auto-response

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ChargebackResponder:
    def __init__(self, model_path: str = "models/classifier.pkl",
                 win_model_path: str = "models/win_predictor.pkl"):
        self.classifier = DisputeClassifier.load(model_path)
        self.win_predictor = None
        try:
            from src.models.win_predictor import WinPredictor
            abs_win_path = os.path.join(_PROJECT_ROOT, win_model_path) if not os.path.isabs(win_model_path) else win_model_path
            if os.path.exists(abs_win_path):
                self.win_predictor = WinPredictor.load(abs_win_path)
            elif os.path.exists(win_model_path):
                self.win_predictor = WinPredictor.load(win_model_path)
        except Exception:
            self.win_predictor = None

    def process(self, dispute: dict) -> dict:
        """Run the full chargeback auto-responder pipeline."""
        # Step 1: Classify reason code
        classification = self.classifier.predict(dispute)
        top_k = self.classifier.predict_top_k(dispute, k=3)

        # Step 2: Retrieve evidence
        evidence = retrieve_evidence(dispute, classification["predicted_reason_code"])

        # Step 3: Predict win probability
        win_probability = None
        if self.win_predictor is not None:
            try:
                win_probability = self.win_predictor.predict_win_probability(dispute)
            except Exception:
                win_probability = None

        # Step 4: Compute expected value
        expected_value = (
            (win_probability * SAVINGS_TP)
            - ((1 - win_probability) * COST_FP)
        ) if win_probability is not None else 0.0

        # Step 5: Generate response template
        response = generate_response(dispute, classification, evidence)
        if win_probability is None:
            response["action"] = "HUMAN_REVIEW"
            response["decision_status"] = "degraded_missing_win_model"

        # Step 6: Build reasoning chain
        reasoning = self._build_reasoning(
            classification, evidence, win_probability, expected_value, response
        )

        return {
            "dispute_id": dispute.get("dispute_id"),
            "classification": {
                **classification,
                "top_k_predictions": top_k,
            },
            "evidence": evidence,
            "win_probability": round(win_probability, 4) if win_probability is not None else None,
            "expected_value_inr": round(expected_value, 2),
            "response": response,
            "reasoning": reasoning,
        }

    def _build_reasoning(self, classification, evidence, win_prob, ev, response):
        """Build human-readable reasoning chain for the decision."""
        steps = []
        rc = classification["predicted_reason_code"]
        conf = classification["confidence"]

        steps.append(
            f"Reason code classified as '{rc}' with {conf:.1%} calibrated confidence."
        )

        strength = evidence["evidence_strength"]
        compelling = evidence["compelling_hits"]
        total_compelling = evidence["compelling_total"]
        steps.append(
            f"Evidence strength: {strength:.1%} "
            f"({compelling}/{total_compelling} compelling pieces matched)."
        )

        if evidence.get("evidence_package", {}).get("missing"):
            missing = ", ".join(evidence["evidence_package"]["missing"])
            steps.append(f"Missing evidence fields: {missing}.")

        steps.append(f"Calibrated win probability: {win_prob:.1%}.")
        steps.append(
            f"Expected value of auto-response: ₹{ev:,.0f} "
            f"(using COST_FP=₹{COST_FP:,}, SAVINGS_TP=₹{SAVINGS_TP:,})."
        )

        action = response["action"]
        if action == "AUTO_SUBMIT":
            steps.append(
                "DECISION: AUTO_SUBMIT — confidence and evidence strength "
                "both exceed threshold gates."
            )
        else:
            steps.append(
                "DECISION: HUMAN_REVIEW — one or more threshold gates not met; "
                "routing to analyst for manual review."
            )

        return steps


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.run <dispute.json>")
        raise SystemExit(1)

    responder = ChargebackResponder()
    with open(sys.argv[1]) as fh:
        dispute = json.load(fh)
    result = responder.process(dispute)
    print(json.dumps(result, indent=2, default=str))
