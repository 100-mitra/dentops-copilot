# CLAUDE.md — build & deploy guide for Claude Code

You are Claude Code. This repo is a **finalized scaffold** for **DentOps Copilot**, an MCP-native agentic dental copilot. Your job: complete the stubbed files, get it running locally, then help deploy it. Read this whole file first.

The longer design doc is `SPEC.md` (and the original brief `docs/BRIEF.md`). This file is the operational guide.

## What's already here vs. what you build

**Provided (reference — verify against installed versions):**
- Root config + deploy: `requirements.txt`, `.env.example`, `docker-compose.yml`, `Dockerfile`, `Makefile`, `render.yaml`, `.github/workflows/ci.yml`
- Backend spine: `backend/config.py`, `backend/mcp_server.py`, `backend/app.py`, `backend/agent/events.py`, `backend/agent/orchestrator.py`, `backend/agent/mcp_client.py`, `backend/tools/detector.py`, `backend/fixtures/detector_outputs.json`
- Frontend reference: `frontend/src/App.tsx`
- Deploy guide: `docs/DEPLOY.md`

**You create (from SPEC + stubs):**
- `backend/__init__.py`, `backend/agent/__init__.py`, `backend/tools/__init__.py`, `backend/db/__init__.py` (package markers)
- `backend/tools/patients.py`, `backend/tools/insurance.py`, `backend/tools/drafting.py`
- `backend/db/models.py` (SQLModel) + `backend/db/seed.py` (~15 patients incl. #1042)
- `backend/tests/test_tools.py` (tool contracts + a grounding "no-invention" test)
- the rest of the Vite app: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`

## Hard guardrails (do not violate)

1. **Do not train or fine-tune any model.** Imaging is a third-party/mock `DetectorBackend`. Default = `MockDetector` reading `fixtures/detector_outputs.json`.
2. **No clinical/diagnostic claims** anywhere (code, UI, README, commits). Never "clinical-grade", "diagnosis", "accurate detection", or imply FDA/CDSCO validity. All generated artifacts are **drafts labelled "for dentist review."**
3. **No auto-execution** of real actions — `propose_actions` only writes proposals.
4. **≤ 5 MCP tools.** Don't add tools.
5. **Grounding rule:** the agent/draft text may only use facts returned by tools. Never invent findings, codes, or patient data. The "no-invention" test must pass.
6. **No secrets in git.** `ANTHROPIC_API_KEY` comes from `.env` (gitignored). Commit only `.env.example`.

## Agent: real Claude over MCP (the user has an API key)

- The orchestrator (`backend/agent/orchestrator.py`) runs a **Claude tool-use loop**: it lists the MCP server's tools, exposes them to Claude as tools, and on each `tool_use` calls the tool **through the MCP client** (`backend/agent/mcp_client.py`) — do not import tool functions directly.
- Each step emits a typed event (`backend/agent/events.py`) onto an `asyncio.Queue`; `/ws` streams them to the UI.
- Key + model come from env: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default `claude-sonnet-4-6`).
- **Verify the current `anthropic` and `fastmcp` APIs before relying on the reference snippets** — they move. Introspect the installed packages.

## Canonical demo (build around this)

New bitewing `fixture:bitewing_1042` for patient `1042` → `read_radiograph` → `get_history` → `draft_patient_summary` → `check_insurance_eligibility(procedure_code="D2740")` → `draft_treatment_plan` → `propose_actions` (flag low-confidence #3, propose 6-month recall). The UI streams every step; drafts show a "for dentist review" banner. Match the look of `docs/prototype.html`.

## Order of work

1. `python -m venv .venv && pip install -r requirements.txt` (or `make install`). Add the `__init__.py` files.
2. Implement `db/models.py` + `db/seed.py`; run `make seed`.
3. Finish `tools/patients.py`, `tools/insurance.py`, `tools/drafting.py` (drafts are **deterministic grounded templates** from inputs — no LLM inside tools).
4. Confirm `mcp_server.py` lists 5 tools + resources + prompts (run it; test with an MCP client).
5. Implement the Claude loop in `orchestrator.py`; `make demo` should run the scenario headless and print the event stream.
6. Run `make dev`; confirm `/demo` streams events over `/ws`.
7. Build the rest of the Vite app; confirm the dashboard renders the live timeline + drafts.
8. Write tests; `make test` green. Then `docs/DEPLOY.md`.

## Commands

- `make install` · `make seed` · `make demo` · `make dev` (uvicorn + vite) · `make test` · `make lint`
- `docker compose up` runs Postgres + API.

## Definition of done

`make dev` runs locally; the canonical demo streams live in the browser; the MCP server runs in Claude Desktop via `docs/claude_desktop_config.md`; CI green; no secrets committed; README has "what's third-party" + "not clinical" sections; deployed per `docs/DEPLOY.md`.
