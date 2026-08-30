"""Evidence retriever.

Maps a (predicted) reason code to the evidence checklist required by the card
network, then scores the evidence actually available in the dispute record.

This is deliberately rule-based rather than learned: the reason-code-to-
evidence mapping is derived from published Visa/Mastercard representment
specifications, which are fixed, public, and non-negotiable. A financial
decision system built on top of a black-box learned mapping here would be
harder to audit and harder to defend to a card network or regulator than one
built on an explicit, inspectable rule table. The ML budget is spent instead
on the part of the problem that genuinely requires it: predicting which
reason code applies and how confident that prediction is.

Rules are expressed against fields that exist in the synthetic schema. Each
expression is either a bare field name (truthy check) or ``field=='value'``
(equality check).
"""

EVIDENCE_RULES = {
    "10.4": {  # Visa: Fraud - Card Absent
        "compelling": ["avs_cvv_match=='both_match'", "has_3ds_authentication",
                       "ip_geolocation_match"],
        "supporting": ["delivery_confirmed", "has_delivery_proof"],
        "template": "fraud_card_absent.j2",
    },
    "10.5": {  # Visa: Fraud - Counterfeit
        "compelling": ["has_3ds_authentication", "avs_cvv_match=='both_match'"],
        "supporting": ["ip_geolocation_match", "delivery_confirmed"],
        "template": "fraud_counterfeit.j2",
    },
    "13.1": {  # Visa: Merchandise Not Received
        "compelling": ["has_delivery_proof", "delivery_confirmed"],
        "supporting": ["has_customer_correspondence"],
        "template": "merchandise_not_received.j2",
    },
    "13.3": {  # Visa: Not as Described
        "compelling": ["has_customer_correspondence", "delivery_confirmed"],
        "supporting": ["has_delivery_proof"],
        "template": "not_as_described.j2",
    },
    "13.6": {  # Visa: Credit Not Processed
        "compelling": ["has_customer_correspondence", "delivery_confirmed"],
        "supporting": ["has_delivery_proof"],
        "template": "credit_not_processed.j2",
    },
    "4837": {  # Mastercard: No Cardholder Authorization
        "compelling": ["has_3ds_authentication", "avs_cvv_match=='both_match'",
                       "ip_geolocation_match"],
        "supporting": ["delivery_confirmed"],
        "template": "no_cardholder_authorization.j2",
    },
    "4853": {  # Mastercard: Cardholder Dispute - Defective
        "compelling": ["has_customer_correspondence", "delivery_confirmed"],
        "supporting": ["has_delivery_proof"],
        "template": "cardholder_dispute_defective.j2",
    },
    "4855": {  # Mastercard: Goods or Services Not Provided
        "compelling": ["has_delivery_proof", "delivery_confirmed"],
        "supporting": ["has_customer_correspondence"],
        "template": "goods_not_provided.j2",
    },
    "4863": {  # Mastercard: Cardholder Does Not Recognize
        "compelling": ["ip_geolocation_match", "has_customer_correspondence"],
        "supporting": ["avs_cvv_match=='both_match'", "delivery_confirmed"],
        "template": "does_not_recognize.j2",
    },
    "4860": {  # Mastercard: Credit Not Processed
        "compelling": ["has_customer_correspondence", "delivery_confirmed"],
        "supporting": ["has_delivery_proof"],
        "template": "credit_not_processed.j2",
    },
}


def _evaluate_expr(expr: str, dispute: dict):
    """Return (field_name, hit_bool, value) for one evidence expression."""
    if "==" in expr:
        field, expected = expr.split("==", 1)
        field = field.strip()
        expected = expected.strip().strip("'\"")
        value = dispute.get(field)
        return field, (str(value) == expected), value

    field = expr.strip()
    value = dispute.get(field)
    return field, bool(value), value


def retrieve_evidence(dispute: dict, predicted_rc: str) -> dict:
    """Score available evidence against what's needed for this reason code."""
    rules = EVIDENCE_RULES.get(predicted_rc, {})
    compelling_exprs = rules.get("compelling", [])
    supporting_exprs = rules.get("supporting", [])

    compelling_total = len(compelling_exprs)
    supporting_total = len(supporting_exprs)

    evidence_package = {"compelling": [], "supporting": [], "missing": []}
    compelling_hits = 0
    supporting_hits = 0

    for expr in compelling_exprs:
        field, hit, value = _evaluate_expr(expr, dispute)
        if hit:
            compelling_hits += 1
            evidence_package["compelling"].append({"field": field, "value": value})
        else:
            evidence_package["missing"].append(field)

    for expr in supporting_exprs:
        field, hit, value = _evaluate_expr(expr, dispute)
        if hit:
            supporting_hits += 1
            evidence_package["supporting"].append({"field": field, "value": value})

    strength = 0.0
    if compelling_total > 0:
        strength += (compelling_hits / compelling_total) * 0.7
    if supporting_total > 0:
        strength += (supporting_hits / supporting_total) * 0.3

    return {
        "evidence_package": evidence_package,
        "evidence_strength": round(strength, 3),
        "compelling_hits": compelling_hits,
        "compelling_total": compelling_total,
        "supporting_hits": supporting_hits,
        "supporting_total": supporting_total,
        "template_name": rules.get("template", "generic.j2"),
        "auto_respond_eligible": strength >= 0.6 and compelling_hits >= 2,
    }
