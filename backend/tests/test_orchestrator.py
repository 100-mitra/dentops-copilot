"""Async orchestrator test: drives the REAL run_demo loop with a fake Claude
client over the REAL MCP tools (in-memory FastMCP Client). No API key, no network.

This locks in the glue that matters: each Claude tool_use is routed through the
MCP protocol, structured results come back, and the right typed events are
emitted (tool_call/tool_result, draft per kind, flag on low-confidence, final).
"""
from types import SimpleNamespace

from fastmcp import Client

from backend.agent import orchestrator
from backend.mcp_server import mcp


# --- fakes -----------------------------------------------------------------
def _text(t):
    return SimpleNamespace(type="text", text=t)


def _tool_use(name, inp, id):
    return SimpleNamespace(type="tool_use", name=name, input=inp, id=id)


# Scripted canonical-demo trajectory; one create() call returns one turn.
_TURNS = [
    (["Planning the case.", ("read_radiograph", {"image_ref": "fixture:bitewing_1042"}, "t1")], "tool_use"),
    ([("get_history", {"patient_id": "1042"}, "t2")], "tool_use"),
    ([("draft_document", {"kind": "patient_summary",
       "context": {"findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}]}}, "t3")], "tool_use"),
    ([("check_insurance_eligibility", {"patient_id": "1042", "procedure_code": "D2740"}, "t4")], "tool_use"),
    ([("draft_document", {"kind": "treatment_plan",
       "context": {"findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
                   "procedure_code": "D2740", "eligibility": {"needs_preauth": True}}}, "t5"),
      ("draft_document", {"kind": "insurance_narrative",
       "context": {"findings": [{"tooth_region": "#14", "label": "caries", "confidence": 0.91}],
                   "procedure_code": "D2740",
                   "eligibility": {"required_attachments": ["bitewing", "narrative"]}}}, "t6")], "tool_use"),
    ([("propose_actions", {"patient_id": "1042",
       "actions": [{"type": "flag", "tooth": "#3"}, {"type": "recall", "interval": "6mo"}]}, "t7")], "tool_use"),
    (["Done — all outputs are drafts for dentist review."], "end_turn"),
]


def _build_turn(spec):
    blocks, stop = spec
    content = []
    for b in blocks:
        content.append(_text(b) if isinstance(b, str) else _tool_use(*b))
    return SimpleNamespace(content=content, stop_reason=stop)


class _FakeMessages:
    def __init__(self):
        self._i = 0

    async def create(self, **kwargs):
        turn = _build_turn(_TURNS[self._i])
        self._i += 1
        return turn


class _FakeAnthropic:
    def __init__(self, *a, **k):
        self.messages = _FakeMessages()


# in-memory MCP client shim matching orchestrator.mcp_client's surface
async def _list_tools():
    async with Client(mcp) as c:
        return await c.list_tools()


async def _call_tool(name, arguments):
    async with Client(mcp) as c:
        return await c.call_tool(name, arguments)


async def test_run_demo_emits_canonical_event_stream(monkeypatch):
    monkeypatch.setattr(orchestrator, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(orchestrator.anthropic, "AsyncAnthropic", _FakeAnthropic)
    monkeypatch.setattr(orchestrator.mcp_client, "list_tools", _list_tools)
    monkeypatch.setattr(orchestrator.mcp_client, "call_tool", _call_tool)

    events = []

    async def emit(e):
        events.append(e)

    await orchestrator.run_demo(emit)

    by_type: dict[str, list] = {}
    for e in events:
        by_type.setdefault(e["type"], []).append(e)

    # every tool was called THROUGH the MCP client
    called = {e["tool"] for e in by_type.get("tool_call", [])}
    assert called == {
        "read_radiograph", "get_history", "check_insurance_eligibility",
        "draft_document", "propose_actions",
    }

    # read_radiograph result carried structured findings for the UI overlay
    rr = next(e for e in by_type["tool_result"] if e["tool"] == "read_radiograph")
    assert [f["tooth_region"] for f in rr["findings"]] == ["#14"]
    assert [f["tooth_region"] for f in rr["low_confidence"]] == ["#3"]

    # three grounded drafts, each disclaimed
    kinds = {e["kind"] for e in by_type.get("draft", [])}
    assert kinds == {"patient_summary", "treatment_plan", "insurance_narrative"}
    assert all(e["disclaimer"] == "DRAFT — for dentist review" for e in by_type["draft"])

    # low-confidence #3 surfaced as a flag; run concluded
    assert any("#3" in e["text"] for e in by_type.get("flag", []))
    assert by_type.get("final")


async def test_run_demo_without_key_emits_error(monkeypatch):
    monkeypatch.setattr(orchestrator, "ANTHROPIC_API_KEY", "")
    events = []

    async def emit(e):
        events.append(e)

    await orchestrator.run_demo(emit)
    assert events and events[0]["type"] == "error"
