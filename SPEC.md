# SPEC — DentOps Copilot (design contract)

Condensed contract. Full narrative: `docs/BRIEF.md`. Operational guide: `CLAUDE.md`.

## Goal
An MCP-native agent that, for a dental X-ray + patient record, orchestrates MCP tools to detect findings, pull history, draft a patient summary + insurance pre-auth narrative, and propose a recall — streaming each step to a React dashboard over WebSocket. Outputs are drafts for dentist review. Not a medical device.

## MCP surface — exactly 5 tools
1. `read_radiograph(image_ref) -> RadiographFindings{findings[], low_confidence[]}` — third-party/mock detector; splits on `CONFIDENCE_THRESHOLD`.
2. `get_history(patient_id) -> dict` — visits, procedures (CDT codes), allergies, prior findings.
3. `check_insurance_eligibility(patient_id, procedure_code) -> dict{covered, needs_preauth, required_attachments, notes}`.
4. `draft_document(kind, context) -> dict{kind, content, disclaimer}` — kind ∈ {patient_summary, treatment_plan, insurance_narrative}; grounded templates only.
5. `propose_actions(patient_id, actions) -> dict` — persists proposals; never executes.

Resources: `patient://{patient_id}`. Prompts: `patient_summary_prompt`, `insurance_narrative_prompt`.

## WebSocket event protocol (`backend/agent/events.py`)
`agent_step{text}` · `tool_call{tool,args}` · `tool_result{tool,summary}` · `draft{kind,content,disclaimer}` · `flag{text}` · `final{text}` · `error{message}`

## Canonical scenario
`fixture:bitewing_1042` for patient `1042` → read_radiograph → get_history → draft_document(patient_summary) → check_insurance_eligibility(D2740) → draft_document(treatment_plan) + draft_document(insurance_narrative) → propose_actions(flag low-confidence #3, 6-month recall). Match `docs/prototype.html`.

## Guardrails
No model training. No clinical/diagnostic claims. ≤5 tools. Grounding: state only tool-returned facts. Drafts labelled "for dentist review". No auto-execution. No secrets in git.
