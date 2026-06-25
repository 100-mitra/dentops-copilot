"""MCP-surface contract test: exercises the server end-to-end through a FastMCP
Client (in-memory transport — no HTTP, no API key). Verifies the exactly-5-tool
contract, the resource template, the prompts, and the read_radiograph split on
the confidence threshold.
"""
import json

import pytest
from fastmcp import Client

from backend.mcp_server import mcp


@pytest.fixture
def client():
    return Client(mcp)


async def test_exactly_five_tools_with_expected_names(client):
    async with client as c:
        tools = await c.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "read_radiograph",
        "get_history",
        "check_insurance_eligibility",
        "draft_document",
        "propose_actions",
    }
    assert len(tools) == 5  # hard ≤5 guardrail


async def test_resource_and_prompts_registered(client):
    async with client as c:
        templates = await c.list_resource_templates()
        prompts = await c.list_prompts()
    assert "patient://{patient_id}" in {t.uriTemplate for t in templates}
    assert {p.name for p in prompts} == {"patient_summary_prompt", "insurance_narrative_prompt"}


async def test_read_radiograph_splits_on_confidence(client):
    async with client as c:
        res = await c.call_tool("read_radiograph", {"image_ref": "fixture:bitewing_1042"})
    data = res.structured_content
    # 0.91 >= threshold (0.7) -> finding; 0.62 < threshold -> low_confidence
    assert [f["tooth_region"] for f in data["findings"]] == ["#14"]
    assert [f["tooth_region"] for f in data["low_confidence"]] == ["#3"]


async def test_patient_resource_reads_record(client):
    async with client as c:
        result = await c.read_resource("patient://1042")
    # resource content is returned as text blocks of JSON
    payload = json.loads(result[0].text)
    assert payload["patient_id"] == "1042"
    assert payload["name"].startswith("Jordan")


async def test_draft_document_is_grounded_and_disclaimed(client):
    async with client as c:
        res = await c.call_tool(
            "draft_document",
            {"kind": "patient_summary", "context": {"findings": []}},
        )
    data = res.structured_content
    assert data["disclaimer"] == "DRAFT — for dentist review"
    assert "#" not in data["content"]  # no invented tooth numbers
