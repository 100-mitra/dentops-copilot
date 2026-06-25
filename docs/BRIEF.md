# DentOps Copilot — Claude Code Project Brief

> **You are Claude Code. This file is your spec.** Build the project described here, phase by phase.
> Rename this to `SPEC.md` (or paste into `CLAUDE.md`) in the repo root once you scaffold.
> Read the whole file before writing any code. If something is genuinely ambiguous or blocked, ask; otherwise proceed with the defaults given here.

Prepared 2026-06-24 · Target: a portfolio prototype for a "AI Engineer Intern (Full-Stack + Agentic AI)" application.

---

## 1. Mission (what we're building)

An **MCP-native agentic copilot for a dental practice**. Given a dental X-ray + a patient record, a Claude agent **orchestrates several MCP tools** to: detect findings (third-party/mock detector), pull patient history, draft a grounded patient-friendly summary and an insurance pre-authorization narrative, and propose a recall — **streaming every reasoning step and tool call live** to a React dashboard. Everything is exposed through a clean **FastAPI + FastMCP server** that any MCP client (including Claude Desktop) can call.

This is a **capability + domain-interest demo**, not a product and not a medical device.

## 2. Non-goals & guardrails (READ — these are hard rules)

These exist to keep the project honest and on-scope. Do not violate them.

- ❌ **Do NOT train or fine-tune any ML model.** Imaging detection is a **third-party/mock** component behind an interface. The default detector is a deterministic mock.
- ❌ **No clinical/diagnostic claims anywhere** — not in code comments, UI text, README, or commit messages. Never use "clinical-grade," "diagnosis," "accurate detection," or imply FDA/CDSCO validity. The UI and all generated artifacts are **DRAFTS labeled "for dentist review."**
- ❌ **No auto-execution of real-world actions.** `schedule_recall` / `flag_for_dentist` write *proposed* actions to the DB only.
- ❌ **Do not exceed 5 MCP tools.** Resist scope creep. More tools ≠ better.
- ✅ **Grounding rule:** the agent may only state facts returned by tools. If a value isn't in a tool result, it must say it doesn't have it — never invent findings, codes, or patient data.
- ✅ **Honest README:** include a "What I built vs. what's third-party" section and an explicit "Limitations & not-clinical" section.
- ✅ **Confidence-gating:** detector findings below a threshold are surfaced as "low confidence — flagged for dentist," never asserted as fact.
- ✅ **No secrets in git.** API keys via `.env` (gitignored); commit `.env.example`.
- ✅ **Keep dependencies minimal and current.** Don't add a library unless a phase needs it.

## 3. Tech stack (pinned — don't substitute without reason)

**Backend**
- Python **3.11+**
- **`fastmcp`** (FastMCP v2 — `pip install fastmcp`, docs: gofastmcp.com) for the MCP server (tools/resources/prompts). It mounts into FastAPI and supports stdio + streamable-HTTP.
- **FastAPI** + **uvicorn** for the web app (WebSocket dashboard endpoint + mounting the MCP app).
- **Pydantic v2** for all tool I/O schemas.
- **SQLModel** (SQLAlchemy) over **PostgreSQL** (via docker-compose). `DATABASE_URL` may point to SQLite for fast local dev.
- **`anthropic`** Python SDK for the Claude agent loop.
- **`pydicom`** (DICOM input) + **Pillow** (PNG/JPEG) for `read_radiograph`.
- **pytest** + **pytest-asyncio** for tests.

**Frontend**
- **React + TypeScript + Vite**, **Tailwind CSS**. Native **WebSocket** client. Keep it one small app; no state-management library needed.

**Tooling:** ruff (lint/format), Docker + docker-compose, GitHub Actions CI, Makefile.

> ⚠️ **API-accuracy rule:** MCP/FastMCP and the Anthropic SDK evolve. **Do not hardcode API calls from memory.** After install, check the installed version and follow its actual API (introspect the package and read its README/docs). The code snippets below are *reference patterns to verify*, not gospel.

## 4. Repository structure (create this)

```
dentops-copilot/
├── README.md                  # honest framing + demo links + run instructions
├── SPEC.md                    # this brief
├── .env.example
├── docker-compose.yml         # postgres + api
├── Dockerfile
├── Makefile
├── pyproject.toml
├── .github/workflows/ci.yml
├── backend/
│   ├── app.py                 # FastAPI app: mounts MCP app + /ws WebSocket + /demo
│   ├── mcp_server.py          # FastMCP server: tools, resources, prompts
│   ├── agent/
│   │   ├── orchestrator.py    # Claude tool-use loop over an MCP client; emits events
│   │   ├── mcp_client.py      # connects to the MCP server, list/call tools
│   │   └── events.py          # WS event types (Pydantic)
│   ├── tools/
│   │   ├── detector.py        # DetectorBackend interface + MockDetector (default)
│   │   ├── patients.py        # lookup_patient / get_history (DB)
│   │   ├── insurance.py       # check_insurance_eligibility (mock payer rules)
│   │   └── drafting.py        # draft_patient_summary / draft_treatment_plan (grounded)
│   ├── db/
│   │   ├── models.py          # SQLModel models
│   │   └── seed.py            # ~15 realistic patients + CDT codes
│   ├── fixtures/              # sample X-rays (DENTEX sample) + mock detector outputs
│   └── tests/
├── frontend/                  # React + Vite + TS + Tailwind
│   └── src/ ...
└── docs/
    └── claude_desktop_config.md  # stdio MCP config snippet
```

## 5. MCP surface (the contract)

Implement in `mcp_server.py` with FastMCP. **Exactly these 5 tools**, plus resources and prompts. Every tool returns a Pydantic model (structured output).

**Tools**

1. `read_radiograph(image_ref: str) -> RadiographFindings`
   - Loads an image by ref (a fixture id, or path). Accepts **DICOM** (`pydicom`) and **PNG/JPEG** (Pillow).
   - Calls the active `DetectorBackend`. Default = `MockDetector` (deterministic findings per fixture).
   - Returns: `findings: list[Finding]` where `Finding = {tooth_region, label, confidence, bbox}`; plus `low_confidence: list[Finding]` (below threshold).
   - **Label clearly in docstring + code: detector is a third-party/placeholder component.**

2. `lookup_patient(query: str) -> list[PatientSummary]` — search seeded patients by name/id.

3. `get_history(patient_id: str) -> PatientHistory` — prior visits, procedures (CDT codes), allergies, prior findings.

4. `check_insurance_eligibility(patient_id: str, procedure_code: str) -> EligibilityResult`
   - Mock payer-rules engine → `{covered: bool, needs_preauth: bool, required_attachments: list[str], notes}`.

5. `draft_patient_summary(findings, history) -> Draft` **and** `draft_treatment_plan(findings, history, eligibility) -> Draft`
   - Implement as **two tools** if under the 5-tool cap by merging recall into history actions, **or** as one `draft(kind, ...)` tool. Prefer two named tools; if that exceeds 5, fold `schedule_recall`/`flag_for_dentist` into a single `propose_actions` tool. **Pick one layout, keep total ≤ 5, document it.**
   - Grounded generation: only use facts present in inputs; output carries a `disclaimer: "DRAFT — for dentist review"`.

(Action tool) `propose_actions(patient_id, actions: list)` — writes proposed `recall` / `flag_for_dentist` rows. Never sends anything.

**Resources** — expose patient records and prior reports as MCP resources (e.g., `patient://{id}`, `report://{id}`) the agent can read.

**Prompts** — register reusable MCP prompts: `patient_summary_prompt`, `insurance_narrative_prompt`. (This satisfies the JD's exact "tools, resources, **and prompts**" wording — don't skip prompts.)

## 6. Agent orchestrator

- `orchestrator.py`: a **Claude tool-use loop** (Anthropic SDK) that connects to the MCP server **through an MCP client** (`mcp_client.py`) — list tools, call tools over the protocol. **Do not import the tool functions directly**; the point is to exercise MCP end-to-end.
- For each step, emit a typed event (see §7) to an `asyncio.Queue` the WebSocket drains.
- Keep the orchestrator backend-swappable (a thin interface) so a LangGraph implementation could replace it later — but the **default is the direct Anthropic + MCP client loop** (simpler, fewer deps).
- Provide a **canonical demo runner** (`/demo` endpoint + CLI `make demo`) that runs the scenario in §8 against a seeded patient.

## 7. WebSocket event protocol (define once, use on both ends)

`/ws` streams JSON events; define them in `agent/events.py` and mirror the types in the frontend.

```json
{ "type": "agent_step",   "text": "Planning: detect findings, then pull history" }
{ "type": "tool_call",    "tool": "read_radiograph", "args": { "...": "..." } }
{ "type": "tool_result",  "tool": "read_radiograph", "summary": "2 findings, 1 low-confidence" }
{ "type": "draft",        "kind": "patient_summary", "content": "…", "disclaimer": "DRAFT — for dentist review" }
{ "type": "flag",         "reason": "low-confidence finding on #14 — dentist review" }
{ "type": "final",        "content": "Done. 3 drafts + 1 proposed recall." }
{ "type": "error",        "message": "…" }
```

## 8. Canonical demo scenario (build the product around this)

> New bitewing uploaded for **Patient #1042** →
> `read_radiograph` (overlay appears) → `get_history` (prior restoration, same tooth) →
> `draft_patient_summary` (plain-English, grounded) → `check_insurance_eligibility` (pre-auth needed) →
> `draft_treatment_plan` + `propose_actions` (flag a low-confidence finding for dentist; propose 6-month recall).

The **wow** is the agent working live across tools — not detector accuracy.

## 9. Frontend (one screen)

- **Left:** uploaded X-ray with finding overlays (boxes from `read_radiograph`).
- **Center:** **live agent timeline** — render each `agent_step` / `tool_call` / `tool_result` as it streams over WebSocket.
- **Right:** draft artifacts (patient summary, treatment plan, insurance narrative) each with a visible **"DRAFT — for dentist review"** banner; low-confidence items badged.
- A "Run demo on Patient #1042" button hits `/demo`.

## 10. Reference wiring (verify against installed versions!)

FastAPI + FastMCP mount (FastMCP v2 pattern — confirm before using):
```python
# backend/app.py  — REFERENCE ONLY, verify the current FastMCP API
from fastapi import FastAPI
from backend.mcp_server import mcp          # a FastMCP instance

mcp_app = mcp.http_app(path="/")            # streamable-http ASGI app
app = FastAPI(lifespan=mcp_app.lifespan)    # MUST share the MCP lifespan
app.mount("/mcp", mcp_app)                  # MCP reachable at /mcp
# ... then add @app.websocket("/ws") and @app.post("/demo")
```
Tool definition (FastMCP):
```python
# REFERENCE — confirm decorator/return conventions in installed fastmcp
from fastmcp import FastMCP
mcp = FastMCP("dentops")

@mcp.tool()
def lookup_patient(query: str) -> list[dict]:
    """Search seeded patients by name or id. (mock data)"""
    ...
```
Also expose a **stdio** entrypoint so the server runs in Claude Desktop; put the config snippet in `docs/claude_desktop_config.md`.

## 11. Build phases (work in order; each ends green & demoable)

**Phase 0 — scaffold.** Repo tree, `pyproject.toml`, ruff, `.env.example`, docker-compose (postgres), Makefile (`install`, `dev`, `test`, `seed`, `demo`, `lint`). DoD: `make install && make lint` pass.

**Phase 1 — MCP server + tools (mock data).** Implement the 5 tools + resources + prompts with `MockDetector` and seeded DB. DoD: server lists tools over MCP; `pytest` covers each tool's contract; a "no-invention" grounding test passes.

**Phase 2 — agent loop (headless).** `orchestrator.py` runs the §8 scenario via the MCP client and prints the event stream. DoD: `make demo` completes the scenario end-to-end in the terminal.

**Phase 3 — FastAPI + WebSocket.** Mount the MCP app; add `/ws` and `/demo`; stream events. DoD: hitting `/demo` streams typed events over `/ws`.

**Phase 4 — React dashboard.** The §9 screen consuming `/ws`. DoD: clicking "Run demo" shows the live timeline, X-ray overlay, and drafts with review banners.

**Phase 5 — harden & ship.** Tests for async paths + grounding; Dockerfile; GitHub Actions CI (lint + test); deploy (backend on Render, frontend on Vercel); record a 90-sec Loom; write the honest README; add Claude Desktop config. DoD: CI green, live demo URL works, README complete.

## 12. Definition of done (whole project)

- One-command local run (`docker compose up` or `make dev`) and a live deployed demo.
- The §8 scenario runs live in the browser with streamed agent steps.
- MCP server runs in Claude Desktop via the documented stdio config.
- CI is green; no secrets in git; README has "what's third-party" + "not clinical" sections.
- No clinical/diagnostic claims anywhere; all outputs labeled drafts.

## 13. How to work (instructions to Claude Code)

1. Read this whole file. Scaffold Phase 0 first; commit per phase with clear messages.
2. **Verify SDK APIs against installed versions** before writing MCP/Anthropic calls — don't trust the reference snippets blindly.
3. Keep a short `docs/BUILD_LOG.md` noting decisions and any deviations from this spec.
4. Write tests as you go; never mark a phase done with failing tests.
5. If blocked or genuinely ambiguous, stop and ask — otherwise proceed with the defaults here.
6. Respect every item in §2. If a request (even mine) conflicts with the honesty guardrails, flag it.

## 14. References (consult for current APIs)
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk · https://pypi.org/project/mcp/
- FastMCP v2 docs (HTTP/FastAPI mounting): https://gofastmcp.com/deployment/http
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- DENTEX sample X-rays (CC-BY, for fixtures only): https://huggingface.co/datasets/ibrahimhamamci/DENTEX
- Example DICOM MCP (landscape awareness — do not copy wholesale): https://github.com/ChristianHinge/dicom-mcp
