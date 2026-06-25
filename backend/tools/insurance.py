"""Mock payer-rules engine. Illustrative only — not real coverage data."""

_RULES = {
    "D2740": {"covered": True, "needs_preauth": True, "required_attachments": ["bitewing", "narrative"]},
    "D2392": {"covered": True, "needs_preauth": False, "required_attachments": []},
}


def check(patient_id: str, procedure_code: str) -> dict:
    rule = _RULES.get(
        procedure_code,
        {"covered": False, "needs_preauth": True, "required_attachments": ["narrative"]},
    )
    return {
        "patient_id": patient_id,
        "procedure_code": procedure_code,
        **rule,
        "notes": "Mock payer rules — illustrative only.",
    }
