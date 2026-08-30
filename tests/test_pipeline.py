"""End-to-end pipeline tests."""

from src.data.generate_disputes import build_dataset
from src.pipeline.run import ChargebackResponder


def test_end_to_end(trained_model):
    responder = ChargebackResponder(trained_model)
    dispute = build_dataset(n=1).iloc[0].to_dict()
    result = responder.process(dispute)
    assert set(result.keys()) == {"dispute_id", "classification", "evidence", "response"}
    assert result["response"]["action"] in {"AUTO_SUBMIT", "HUMAN_REVIEW"}
    assert isinstance(result["response"]["response_text"], str)
    assert result["response"]["response_text"].strip() != ""


def test_low_confidence_never_auto_submits(trained_model):
    """Kill-switch semantics: an ineligible evidence package must go to review."""
    responder = ChargebackResponder(trained_model)
    dispute = build_dataset(n=1).iloc[0].to_dict()
    for f in ["avs_cvv_match", "has_3ds_authentication", "ip_geolocation_match",
              "delivery_confirmed", "has_delivery_proof", "has_customer_correspondence"]:
        dispute[f] = False
    dispute["avs_cvv_match"] = "neither"
    result = responder.process(dispute)
    assert result["response"]["action"] == "HUMAN_REVIEW"
