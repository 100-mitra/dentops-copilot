"""Grounded draft generation + proposed actions.

Drafts are DETERMINISTIC TEMPLATES built ONLY from the context passed in — no LLM
inside the tool, no invented facts. Every clause is gated on a field actually
being present in `context`, so the grounding ('no-invention') test holds: with
empty/absent inputs the template emits nothing fabricated (no tooth numbers, no
procedure codes). The agent decides what grounded context to pass.

All output carries disclaimer "DRAFT — for dentist review". propose_actions only
records proposals — it never sends or executes anything.
"""
from __future__ import annotations

_DISCLAIMER = "DRAFT — for dentist review"


# The agent chooses the context shape, so look in the common places an LLM puts
# detector output. Still grounded: only ever reads values actually present.
_RADIOGRAPH_KEYS = ("radiograph_findings", "radiograph", "detector", "radiograph_result", "findings_result")


def _as_finding_list(v) -> list[dict]:
    return [f for f in v if isinstance(f, dict)] if isinstance(v, list) else []


def _findings(context: dict) -> list[dict]:
    out = _as_finding_list(context.get("findings"))
    if out:
        return out
    for key in _RADIOGRAPH_KEYS:
        sub = context.get(key)
        if isinstance(sub, dict):
            for sk in ("findings", "high_confidence", "high"):
                out = _as_finding_list(sub.get(sk))
                if out:
                    return out
    for sk in ("high_confidence", "high"):
        out = _as_finding_list(context.get(sk))
        if out:
            return out
    return []


def _low_confidence(context: dict) -> list[dict]:
    out = _as_finding_list(context.get("low_confidence"))
    if out:
        return out
    for key in _RADIOGRAPH_KEYS:
        sub = context.get(key)
        if isinstance(sub, dict):
            for sk in ("low_confidence", "low"):
                out = _as_finding_list(sub.get(sk))
                if out:
                    return out
    return _as_finding_list(context.get("low"))


def _fmt_findings(findings: list[dict]) -> str:
    parts = [
        f"{f.get('tooth_region')} {f.get('label')} (conf {f.get('confidence')})".strip()
        for f in findings
    ]
    return ", ".join(p for p in parts if p) or "no high-confidence findings"


def _fmt_low(low: list[dict]) -> str:
    regions = [str(f.get("tooth_region")) for f in low if f.get("tooth_region")]
    return ", ".join(regions)


def _history(context: dict) -> dict:
    h = context.get("history")
    return h if isinstance(h, dict) else {}


def _eligibility(context: dict) -> dict:
    e = context.get("eligibility")
    if isinstance(e, dict):
        return e
    # accept flattened eligibility fields placed at the top level
    return {k: context[k] for k in ("covered", "needs_preauth", "required_attachments", "notes") if k in context}


def _procedure_code(context: dict) -> str:
    for k in ("procedure_code", "procedure", "code"):
        v = context.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _prior_clause(context: dict) -> str:
    """A grounded mention of a prior restoration, if history provides one."""
    prior = _history(context).get("prior_findings") or context.get("prior_findings") or []
    teeth = [str(p.get("tooth_region")) for p in prior if isinstance(p, dict) and p.get("tooth_region")]
    if teeth:
        return f" Prior restoration on record for {', '.join(teeth)}."
    return ""


def draft(kind: str, context: dict) -> dict:
    findings = _findings(context)
    low = _low_confidence(context)
    low_str = _fmt_low(low)

    if kind == "patient_summary":
        if findings:
            content = f"Your recent X-ray shows: {_fmt_findings(findings)}."
        else:
            content = "Your recent X-ray shows no high-confidence findings to report."
        content += _prior_clause(context)
        if low_str:
            content += f" A smaller area on {low_str} was uncertain and will be checked by your dentist."
        else:
            content += " Any uncertain areas will be checked by your dentist."

    elif kind == "treatment_plan":
        proc = _procedure_code(context)
        elig = _eligibility(context)
        head = f"Recommended: {proc}" if proc else "Recommended: pending dentist confirmation"
        content = f"{head}, based on {_fmt_findings(findings)}.{_prior_clause(context)}"
        if low_str:
            content += f" Monitor {low_str} (low confidence — for dentist review)."
        if elig.get("needs_preauth"):
            content += " Pre-authorisation is required before treatment."

    elif kind == "insurance_narrative":
        proc = _procedure_code(context)
        elig = _eligibility(context)
        attachments = ", ".join(elig.get("required_attachments") or context.get("required_attachments") or []) or "as required"
        content = f"Radiographic evidence: {_fmt_findings(findings)}.{_prior_clause(context)}"
        content += f" Requesting pre-authorisation for {proc}." if proc else " Requesting pre-authorisation."
        content += f" Attachments: {attachments}."

    else:
        content = "Unknown draft kind."

    return {"kind": kind, "content": content, "disclaimer": _DISCLAIMER}


_PROPOSED: list[dict] = []  # in-memory record; intentionally NOT executed/sent.


def propose_actions(patient_id: str, actions: list[dict]) -> dict:
    record = {"patient_id": patient_id, "actions": actions, "status": "proposed"}
    _PROPOSED.append(record)
    return {**record, "note": "Proposed only — nothing was sent or executed."}
