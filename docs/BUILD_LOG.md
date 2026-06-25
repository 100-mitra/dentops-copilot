# Build log — decisions & deviations

Short notes on what was done to complete the scaffold and where reality differed
from the reference snippets in `SPEC.md` / `CLAUDE.md`.

## Environment (verified, not assumed)
- Python **3.14.2**, Node **24**, npm **11**.
- Installed (via `requirements.txt`): **fastmcp 3.4.2**, **anthropic 0.111.0**,
  **mcp 1.28.0**, fastapi 0.138, sqlmodel 0.0.38, pydantic 2.13, pydicom 3.0.2,
  pillow 12, pytest 9 + pytest-asyncio 1.4, ruff 0.15.

## API verification (the SPEC said to check these — they moved)
- **FastMCP is v3, not v2.** Verified against 3.4.2 that the scaffold's usage still
  holds: bare `@mcp.tool` / `@mcp.prompt`, `@mcp.resource("uri")`, and
  `mcp.http_app(path="/")` → `StarletteWithLifespan` with a `.lifespan` (shared
  with FastAPI). `mcp.run()` defaults to stdio for Claude Desktop. No server-code
  changes were needed.
- **FastMCP `Client` result shape:** `call_tool()` returns a `CallToolResult` with
  `.structured_content` (clean dict — no `result` wrapper for dict/model returns),
  `.content[0].text` (JSON), and `.data`. The orchestrator's `_result_data()`
  (structured_content first) is correct as written. Tool defs expose
  `.name` / `.description` / `.inputSchema` (camelCase) — matches `_anthropic_tools()`.
- **anthropic 0.111.0:** `AsyncAnthropic` + `messages.create(model, max_tokens,
  system, tools, messages)` tool-use loop verified. Model kept at
  **`claude-sonnet-4-6`** (the project's deliberate default in `config.py` /
  `.env.example` / `render.yaml`) — a valid current model id; not overridden.

## Implemented
- `db/models.py`: `Patient` + `Procedure` (CDT-coded), `get_session()`, SQLite
  `check_same_thread=False` (FastMCP runs sync tools across threads).
- `db/seed.py`: **15 patients** incl. demo `#1042`. `SEED_PATIENTS` is importable;
  `run()` is idempotent and **stdout-silent** (printing to stdout would corrupt the
  JSON-RPC stream under stdio transport — logs go to stderr).
- `tools/patients.py`: now **DB-backed** (`record` / `history` / `search`). Prior
  radiographic findings are **derived** from restorative (D2xxx) procedures rather
  than stored — keeps the schema small and every finding traceable to a real row.
  Lazily **auto-seeds** an empty DB on first use so `make demo` / the server work
  even if `make seed` was skipped; `make seed` remains the explicit path.
- `tools/drafting.py`: richer but still **deterministic, grounded** templates —
  every clause is gated on a field actually present in `context`, so the
  no-invention guarantee holds for empty inputs.
- `orchestrator.py`: kept the verified Claude loop; improved per-tool timeline
  summaries and added **flag** events for low-confidence detector findings.

## Deviations / additions
- **Event protocol extension:** added optional `findings` / `low_confidence` to the
  `read_radiograph` `tool_result` event so the dashboard can draw bbox overlays
  from real detector output (SPEC §9). Still grounded — it is the tool's own output.
- **Frontend:** the scaffold lacked `tsconfig.json` — added `tsconfig.json` +
  `tsconfig.node.json`. Rebuilt `App.tsx` to match `docs/prototype.html`
  (3-zone layout, data-driven radiograph overlays, draft cards with review banners,
  WS auto-reconnect) and added `index.css` (prototype design tokens). Tabler icons
  via CDN, as in the prototype.
- **Tooling:** added `pyproject.toml` for pytest (`asyncio_mode=auto`,
  `pythonpath`) and ruff config (default lint set, to avoid churning the provided
  spine files).

## Fix surfaced by a real agent run
- First live run (real key) showed hollow drafts ("no high-confidence findings")
  even though `read_radiograph` returned #14 caries (0.91). Cause: the agent passed
  detector output under varied keys (e.g. `radiograph_findings.high_confidence`) /
  omitted it from the summary call, while the deterministic template only read
  `context["findings"]`. Fixes: (1) `drafting.py` now reads findings / low_confidence
  / eligibility / procedure_code from the common shapes an LLM produces (still
  grounded — only reads values present); (2) the `draft_document` tool description
  now spells out the exact context keys to pass. Re-run produced correct, grounded
  drafts citing #14 caries + #3 flagged. Regression locked by tests.

## Verified working
- `ruff check backend` clean; `pytest` **21 passed** (tool contracts, DB history,
  grounding/no-invention, full MCP surface in-memory, and the async orchestrator
  trajectory driven by a fake Claude client over the real MCP tools — no API key).
- Live: uvicorn `/health` ok, MCP reachable over HTTP at `/mcp` (5 tools, lifespan
  ok), `POST /demo` streams typed events over `/ws` (emits a clean `error` event
  when `ANTHROPIC_API_KEY` is unset). `frontend` builds (`tsc && vite build`).
- A real end-to-end agent run needs a paid `ANTHROPIC_API_KEY` in `.env`.
