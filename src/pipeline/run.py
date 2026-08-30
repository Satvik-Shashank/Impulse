"""Main pipeline: dispute JSON -> full response package.

Usage:
    python -m src.pipeline.run sample_dispute.json
"""

import json
import sys
from src.models.classifier import DisputeClassifier
from src.pipeline.evidence_retriever import retrieve_evidence
from src.pipeline.response_generator import generate_response


class ChargebackResponder:
    def __init__(self, model_path: str = "models/classifier.pkl"):
        self.classifier = DisputeClassifier.load(model_path)

    def process(self, dispute: dict) -> dict:
        classification = self.classifier.predict(dispute)
        evidence = retrieve_evidence(dispute, classification["predicted_reason_code"])
        response = generate_response(dispute, classification, evidence)
        return {
            "dispute_id": dispute.get("dispute_id"),
            "classification": classification,
            "evidence": evidence,
            "response": response,
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.run <dispute.json>")
        raise SystemExit(1)

    responder = ChargebackResponder()
    with open(sys.argv[1]) as fh:
        dispute = json.load(fh)
    result = responder.process(dispute)
    print(json.dumps(result, indent=2, default=str))
