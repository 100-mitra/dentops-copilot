"""Tool-contract + grounding tests. These run in CI without an API key.

Covers: the mock detector, insurance rules, DB-backed patient history (with
derived prior findings), the deterministic grounded drafts, and the core
'no-invention' grounding guarantee.
"""
from backend.tools.detector import MockDetector
from backend.tools import insurance, drafting, patients


# --- detector --------------------------------------------------------------
def test_detector_returns_fixture_findings():
    res = MockDetector().analyze("fixture:bitewing_1042")
    assert len(res) == 2
    assert {f.tooth_region for f in res} == {"#14", "#3"}


def test_detector_unknown_ref_is_empty():
    assert MockDetector().analyze("fixture:does_not_exist") == []


# --- insurance -------------------------------------------------------------
def test_insurance_crown_needs_preauth():
    r = insurance.check("1042", "D2740")
    assert r["covered"] is True
    assert r["needs_preauth"] is True
    assert "bitewing" in r["required_attachments"]


def test_insurance_unknown_code_defaults_to_preauth():
    r = insurance.check("1042", "D9999")
    assert r["needs_preauth"] is True


# --- patients (DB-backed) --------------------------------------------------
def test_history_demo_patient_1042():
    h = patients.history("1042")
    assert h["last_visit"] == "2025-11-12"
    codes = {p["code"] for p in h["procedures"]}
    assert "D2392" in codes
    # prior restoration is DERIVED from the D2392 procedure on #14
    assert {"tooth_region": "#14", "label": "existing restoration"} in h["prior_findings"]


def test_history_unknown_patient():
    h = patients.history("0000")
    assert h.get("error") == "not found"


def test_seed_has_about_fifteen_patients():
    assert len(patients.search("")) >= 15


def test_search_by_name_and_id():
    assert any(p["patient_id"] == "1042" for p in patients.search("1042"))
    assert all("nguyen" in p["name"].lower() for p in patients.search("Nguyen"))


# --- drafting (grounded templates) -----------------------------------------
def test_draft_grounding_no_invention():
    # With no findings the draft must NOT fabricate a tooth number or code.
    out = drafting.draft("patient_summary", {"findings": []})
    assert "#" not in out["content"]
    assert "D27" not in out["content"]
    assert out["disclaimer"] == "DRAFT — for dentist review"


def test_draft_patient_summary_uses_findings_and_low_confidence():
    ctx = {
        "findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
        "low_confidence": [{"tooth_region": "#3", "label": "caries", "confidence": 0.62}],
    }
    out = drafting.draft("patient_summary", ctx)
    assert "#14" in out["content"]
    assert "#3" in out["content"]  # flagged as uncertain


def test_draft_treatment_plan_grounded():
    ctx = {
        "findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
        "procedure_code": "D2740",
        "eligibility": {"needs_preauth": True},
    }
    out = drafting.draft("treatment_plan", ctx)
    assert "D2740" in out["content"]
    assert "pre-authorisation" in out["content"].lower()


def test_draft_insurance_narrative_lists_attachments():
    ctx = {
        "findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
        "procedure_code": "D2740",
        "eligibility": {"required_attachments": ["bitewing", "narrative"]},
    }
    out = drafting.draft("insurance_narrative", ctx)
    assert "bitewing" in out["content"]
    assert "D2740" in out["content"]


def test_draft_treatment_plan_no_invention_when_empty():
    out = drafting.draft("treatment_plan", {"findings": []})
    assert "#" not in out["content"]
    assert "D2" not in out["content"]


def test_draft_tolerates_nested_radiograph_findings_shape():
    # The agent often nests detector output instead of using `findings` directly.
    # The draft must still pick up the real finding (grounded, not invented).
    ctx = {
        "radiograph_findings": {
            "high_confidence": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
            "low_confidence": [{"tooth_region": "#3", "label": "caries", "confidence": 0.62}],
        },
    }
    out = drafting.draft("patient_summary", ctx)
    assert "#14" in out["content"]
    assert "#3" in out["content"]
    assert "no high-confidence findings" not in out["content"]


def test_draft_tolerates_flattened_eligibility_and_procedure():
    ctx = {
        "findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
        "procedure": "D2740",                        # not "procedure_code"
        "needs_preauth": True,                       # eligibility flattened to top level
        "required_attachments": ["bitewing", "narrative"],
    }
    plan = drafting.draft("treatment_plan", ctx)
    assert "D2740" in plan["content"]
    assert "pre-authorisation" in plan["content"].lower()
    narrative = drafting.draft("insurance_narrative", ctx)
    assert "bitewing" in narrative["content"]
    assert "D2740" in narrative["content"]


# --- propose_actions never executes ----------------------------------------
def test_propose_actions_never_executes():
    out = drafting.propose_actions("1042", [{"type": "recall", "interval": "6mo"}])
    assert out["status"] == "proposed"
    assert "nothing was sent" in out["note"].lower()
