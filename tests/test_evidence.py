"""Tests for the evidence retriever (pure logic, no model)."""

from src.pipeline.evidence_retriever import retrieve_evidence, EVIDENCE_RULES


def test_all_reason_codes_have_rules():
    expected = {"10.4", "10.5", "13.1", "13.3", "13.6",
                "4837", "4853", "4855", "4863", "4860"}
    assert expected.issubset(set(EVIDENCE_RULES.keys()))


def test_strong_evidence_is_auto_respond_eligible():
    dispute = {
        "avs_cvv_match": "both_match",
        "has_3ds_authentication": True,
        "ip_geolocation_match": True,
        "delivery_confirmed": True,
        "has_delivery_proof": True,
    }
    ev = retrieve_evidence(dispute, "10.4")
    assert ev["compelling_hits"] == 3
    assert ev["evidence_strength"] >= 0.6
    assert ev["auto_respond_eligible"] is True


def test_weak_evidence_flags_for_review():
    dispute = {
        "avs_cvv_match": "neither",
        "has_3ds_authentication": False,
        "ip_geolocation_match": False,
        "delivery_confirmed": False,
        "has_delivery_proof": False,
    }
    ev = retrieve_evidence(dispute, "10.4")
    assert ev["compelling_hits"] == 0
    assert ev["auto_respond_eligible"] is False
    assert "avs_cvv_match" in ev["evidence_package"]["missing"]


def test_unknown_reason_code_uses_generic():
    ev = retrieve_evidence({}, "99.9")
    assert ev["template_name"] == "generic.j2"
    assert ev["auto_respond_eligible"] is False
