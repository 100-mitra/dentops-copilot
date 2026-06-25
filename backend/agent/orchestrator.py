"""Real Claude tool-use loop over MCP. The user has an ANTHROPIC_API_KEY.

The agent lists the MCP server's tools, exposes them to Claude, and on each
tool_use calls the tool THROUGH the MCP client. Every step is emitted as a typed
event. The agent may only state facts returned by tools (grounding).

Verify the anthropic + fastmcp APIs against installed versions before trusting the
field names below (e.g. tool input_schema, result content shape).
"""
from __future__ import annotations
import argparse
import asyncio
import json

import anthropic

from backend.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from backend.agent import mcp_client, events

SYSTEM = (
    "You are DentOps Copilot, an agent for a dental practice. Use the provided MCP tools "
    "to handle the case. You may ONLY state facts returned by tools — never invent findings, "
    "procedure codes, or patient data. Route any low-confidence finding to the dentist. "
    "Everything you produce is a DRAFT for dentist review. Do not execute real-world actions."
)

DEMO_TASK = (
    "A new bitewing 'fixture:bitewing_1042' was uploaded for patient '1042'. "
    "Detect findings, pull the patient's history, draft a patient summary, check insurance "
    "eligibility for procedure D2740, draft a treatment plan and an insurance narrative, then "
    "propose actions: flag any low-confidence finding for the dentist and propose a 6-month recall."
)


async def _anthropic_tools() -> list[dict]:
    tools = await mcp_client.list_tools()
    # Map MCP tool defs -> Anthropic tool schema. Verify attribute names against installed SDKs.
    return [
        {"name": t.name, "description": (t.description or ""), "input_schema": t.inputSchema}
        for t in tools
    ]


def _result_data(result) -> dict | list | str:
    # TODO(claude-code): FastMCP call_tool returns structured content; normalise to plain JSON.
    # Often: result.structured_content, or json-decoded result.content[0].text. Verify and adapt.
    sc = getattr(result, "structured_content", None)
    if sc is not None:
        return sc
    try:
        return json.loads(result.content[0].text)
    except Exception:
        return str(result)


def _summary(name: str, data) -> str:
    """One-line timeline summary built only from tool output (grounded)."""
    if not isinstance(data, dict):
        return "ok"
    if name == "read_radiograph":
        return f"{len(data.get('findings', []))} findings · {len(data.get('low_confidence', []))} low-confidence"
    if name == "get_history":
        procs = data.get("procedures", [])
        return f"{len(procs)} procedures · last visit {data.get('last_visit', 'n/a')}"
    if name == "check_insurance_eligibility":
        cov = "covered" if data.get("covered") else "not covered"
        pre = "pre-auth required" if data.get("needs_preauth") else "no pre-auth"
        atts = ", ".join(data.get("required_attachments", [])) or "none"
        return f"{cov} · {pre} · attachments: {atts}"
    if name == "draft_document":
        return f"{data.get('kind', 'document')} drafted"
    if name == "propose_actions":
        return f"{len(data.get('actions', []))} action(s) proposed (not sent)"
    return "ok"


async def run_demo(emit, task: str = DEMO_TASK) -> None:
    """emit: async callable taking a dict event."""
    if not ANTHROPIC_API_KEY:
        await emit(events.error("ANTHROPIC_API_KEY not set — add it to .env").model_dump())
        return

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    tools = await _anthropic_tools()
    messages: list[dict] = [{"role": "user", "content": task}]
    await emit(events.agent_step("Planning the case.").model_dump())

    for _ in range(12):  # safety cap on agent turns
        resp = await client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=1024, system=SYSTEM, tools=tools, messages=messages
        )
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                await emit(events.agent_step(block.text.strip()).model_dump())

        if resp.stop_reason != "tool_use":
            await emit(events.final("Done — all outputs are drafts for dentist review.").model_dump())
            return

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            await emit(events.tool_call(block.name, block.input).model_dump())
            result = await mcp_client.call_tool(block.name, block.input)
            data = _result_data(result)
            is_radiograph = block.name == "read_radiograph" and isinstance(data, dict)
            await emit(events.tool_result(
                block.name,
                _summary(block.name, data),
                findings=data.get("findings") if is_radiograph else None,
                low_confidence=data.get("low_confidence") if is_radiograph else None,
            ).model_dump())
            if block.name == "draft_document" and isinstance(data, dict):
                await emit(events.draft(data.get("kind", "draft"), data.get("content", "")).model_dump())
            # Surface low-confidence detector findings as explicit dentist-review flags (grounded).
            if is_radiograph:
                for f in data.get("low_confidence", []):
                    region = f.get("tooth_region", "?")
                    await emit(events.flag(
                        f"Low-confidence finding on {region} — routed to dentist review."
                    ).model_dump())
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(data, default=str)}
            )
        messages.append({"role": "user", "content": tool_results})

    await emit(events.final("Reached turn limit.").model_dump())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.parse_args()

    async def _print(evt: dict) -> None:
        print(evt)

    asyncio.run(run_demo(_print))
