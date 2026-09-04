"""Response generator: fills the network-compliant representment template."""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEMPLATE_DIRS = [os.path.join(_PROJECT_ROOT, "templates"), "templates"]

env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIRS),
    autoescape=select_autoescape(enabled_extensions=(), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Confidence threshold controlling auto-submit. Set to 1.0 to disable all
# auto-responses (kill switch).
AUTO_RESPOND_CONFIDENCE = float(os.getenv("AUTO_RESPOND_CONFIDENCE", "0.70"))


def generate_response(dispute: dict, classification: dict, evidence: dict) -> dict:
    """Fill the representment template with evidence and decide the action."""
    template_name = evidence.get("template_name", "generic.j2")
    try:
        template = env.get_template(template_name)
    except Exception:
        template = env.get_template("generic.j2")

    response_text = template.render(
        dispute_id=dispute.get("dispute_id", "N/A"),
        reason_code=classification["predicted_reason_code"],
        reason_label=dispute.get("reason_code_label", ""),
        card_network=dispute.get("card_network", ""),
        amount=dispute.get("dispute_amount", 0.0),
        currency=dispute.get("currency", "INR"),
        evidence=evidence["evidence_package"],
        evidence_strength=evidence["evidence_strength"],
        confidence=classification["confidence"],
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )

    should_auto_respond = (
        evidence["auto_respond_eligible"]
        and classification["confidence"] >= AUTO_RESPOND_CONFIDENCE
        and classification.get("model_status") != "fallback_unavailable_for_auto_submit"
    )

    return {
        "response_text": response_text,
        "action": "AUTO_SUBMIT" if should_auto_respond else "HUMAN_REVIEW",
        "confidence": classification["confidence"],
        "evidence_strength": evidence["evidence_strength"],
        "missing_evidence": evidence["evidence_package"]["missing"],
    }
