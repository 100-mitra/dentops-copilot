"""Typed WebSocket events streamed to the dashboard. Mirror these types in frontend/src/App.tsx."""
from typing import Any, Literal, Optional
from pydantic import BaseModel

EventType = Literal["agent_step", "tool_call", "tool_result", "draft", "flag", "final", "error"]


class Event(BaseModel):
    type: EventType
    text: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[dict[str, Any]] = None
    summary: Optional[str] = None
    kind: Optional[str] = None
    content: Optional[str] = None
    disclaimer: Optional[str] = None
    message: Optional[str] = None
    # Structured detector output, attached to the read_radiograph tool_result so the
    # dashboard can draw bbox overlays. Grounded — these are the tool's own findings.
    findings: Optional[list[dict[str, Any]]] = None
    low_confidence: Optional[list[dict[str, Any]]] = None


def agent_step(text: str) -> Event:
    return Event(type="agent_step", text=text)


def tool_call(tool: str, args: dict) -> Event:
    return Event(type="tool_call", tool=tool, args=args)


def tool_result(tool: str, summary: str, findings=None, low_confidence=None) -> Event:
    return Event(
        type="tool_result", tool=tool, summary=summary,
        findings=findings, low_confidence=low_confidence,
    )


def draft(kind: str, content: str) -> Event:
    return Event(type="draft", kind=kind, content=content, disclaimer="DRAFT — for dentist review")


def flag(text: str) -> Event:
    return Event(type="flag", text=text)


def final(text: str) -> Event:
    return Event(type="final", text=text)


def error(message: str) -> Event:
    return Event(type="error", message=message)
