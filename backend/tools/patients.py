"""Patient lookup / history tools, backed by SQLModel (backend/db).

Return shapes are deliberately plain dicts (the MCP tools surface them as
structured JSON). Grounding rule: these only ever report rows that exist in the
DB — nothing is invented. `prior_findings` are DERIVED from restorative
procedures (a filling/crown on a tooth implies an existing restoration there),
so they stay traceable to real procedure rows.

The DB is auto-seeded (silently) on first use if empty, so `make demo` / the
server work even if `make seed` was skipped. `make seed` remains the explicit path.
"""
from __future__ import annotations

from sqlmodel import select

from backend.db import seed
from backend.db.models import get_session, init_db, Patient, Procedure

_seed_checked = False


def _ensure_seeded() -> None:
    """Create tables, then seed once per process if empty. STDOUT-silent."""
    global _seed_checked
    if _seed_checked:
        return
    init_db()
    with get_session() as s:
        empty = s.exec(select(Patient).limit(1)).first() is None
    if empty:
        seed.run(verbose=False)
    _seed_checked = True


def _not_found(patient_id: str) -> dict:
    return {"error": "not found", "patient_id": patient_id}


def _procedures(s, patient_id: str) -> list[dict]:
    rows = s.exec(
        select(Procedure).where(Procedure.patient_id == patient_id).order_by(Procedure.date)
    ).all()
    return [{"code": r.code, "desc": r.desc, "tooth": r.tooth, "date": r.date} for r in rows]


def _prior_findings(procedures: list[dict]) -> list[dict]:
    """Derive existing restorations from restorative (D2xxx) procedures on a tooth.

    Grounded: each finding maps to a real procedure row. Deduped per tooth.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for p in procedures:
        tooth = p.get("tooth") or ""
        if tooth and p.get("code", "").startswith("D2") and tooth not in seen:
            seen.add(tooth)
            out.append({"tooth_region": tooth, "label": "existing restoration"})
    return out


def record(patient_id: str) -> dict:
    """Full patient record (for the patient:// MCP resource)."""
    _ensure_seeded()
    with get_session() as s:
        p = s.get(Patient, patient_id)
        if not p:
            return _not_found(patient_id)
        procedures = _procedures(s, patient_id)
        return {
            "patient_id": p.patient_id,
            "name": p.name,
            "last_visit": p.last_visit,
            "allergies": [a for a in p.allergies.split(",") if a],
            "procedures": procedures,
            "prior_findings": _prior_findings(procedures),
        }


def history(patient_id: str) -> dict:
    """Visit/procedure history for the get_history tool (no name/PII beyond id)."""
    _ensure_seeded()
    with get_session() as s:
        p = s.get(Patient, patient_id)
        if not p:
            return _not_found(patient_id)
        procedures = _procedures(s, patient_id)
        return {
            "patient_id": p.patient_id,
            "last_visit": p.last_visit,
            "allergies": [a for a in p.allergies.split(",") if a],
            "procedures": procedures,
            "prior_findings": _prior_findings(procedures),
        }


def search(query: str) -> list[dict]:
    """Search seeded patients by id substring or name (case-insensitive)."""
    _ensure_seeded()
    q = (query or "").strip().lower()
    with get_session() as s:
        patients = s.exec(select(Patient)).all()
    hits = []
    for p in patients:
        if not q or q in p.patient_id.lower() or q in p.name.lower():
            hits.append({"patient_id": p.patient_id, "name": p.name, "last_visit": p.last_visit})
    return hits
