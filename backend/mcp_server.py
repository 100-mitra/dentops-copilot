"""FastMCP server: exactly 5 tools + resources + prompts, over JSON-RPC.

Run standalone for Claude Desktop (stdio):  python -m backend.mcp_server
Mounted over HTTP by backend/app.py for the web agent + dashboard.

NOTE: verify the FastMCP decorator/return conventions against the INSTALLED
fastmcp version before relying on this. APIs move.
"""
from fastmcp import FastMCP

from backend.config import CONFIDENCE_THRESHOLD
from backend.tools.detector import MockDetector, RadiographFindings
from backend.tools import patients, insurance, drafting

mcp = FastMCP("dentops")
_detector = MockDetector()


@mcp.tool
def read_radiograph(image_ref: str) -> RadiographFindings:
    """Detect findings on a dental radiograph. Detector is THIRD-PARTY/MOCK.
    image_ref is a fixture id (or, with a real detector, a DICOM/PNG path)."""
    found = _detector.analyze(image_ref)
    hi = [f for f in found if f.confidence >= CONFIDENCE_THRESHOLD]
    lo = [f for f in found if f.confidence < CONFIDENCE_THRESHOLD]
    return RadiographFindings(findings=hi, low_confidence=lo)


@mcp.tool
def get_history(patient_id: str) -> dict:
    """Return a patient's visit/procedure history (mock data)."""
    return patients.history(patient_id)


@mcp.tool
def check_insurance_eligibility(patient_id: str, procedure_code: str) -> dict:
    """Mock payer-rules check -> {covered, needs_preauth, required_attachments, notes}."""
    return insurance.check(patient_id, procedure_code)


@mcp.tool
def draft_document(kind: str, context: dict) -> dict:
    """Grounded draft from tool outputs ONLY. Must not invent facts.

    kind in {patient_summary, treatment_plan, insurance_narrative}.

    Pass `context` using these exact keys, with values copied verbatim from
    earlier tool results (omit a key if you don't have it — never fabricate):
      - findings:        read_radiograph's `findings` list (high-confidence)
      - low_confidence:  read_radiograph's `low_confidence` list
      - history:         the dict returned by get_history (for prior restorations)
      - eligibility:     the dict returned by check_insurance_eligibility
      - procedure_code:  the procedure being planned, e.g. "D2740"

    Include `findings`/`low_confidence` for EVERY kind so the summary is accurate.
    Returns {kind, content, disclaimer: 'DRAFT — for dentist review'}."""
    return drafting.draft(kind, context)


@mcp.tool
def propose_actions(patient_id: str, actions: list[dict]) -> dict:
    """Persist PROPOSED actions (e.g. recall, dentist flag). Never sends/executes anything."""
    return drafting.propose_actions(patient_id, actions)


# --- Resources -------------------------------------------------------------
@mcp.resource("patient://{patient_id}")
def patient_resource(patient_id: str) -> dict:
    """Expose a patient record as an MCP resource."""
    return patients.record(patient_id)


# --- Prompts ---------------------------------------------------------------
@mcp.prompt
def patient_summary_prompt(findings: str, history: str) -> str:
    return (
        "Write a short, plain-language summary for the patient using ONLY these facts. "
        f"Findings: {findings}. History: {history}. "
        "Do not add anything not present above. End with: DRAFT — for dentist review."
    )


@mcp.prompt
def insurance_narrative_prompt(findings: str, procedure_code: str) -> str:
    return (
        "Draft an insurance pre-authorisation narrative using ONLY these facts. "
        f"Findings: {findings}. Requested procedure: {procedure_code}."
    )


if __name__ == "__main__":
    mcp.run()  # stdio transport for Claude Desktop; verify in installed fastmcp
