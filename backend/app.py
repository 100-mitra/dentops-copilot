"""FastAPI app: mounts the MCP server (streamable HTTP) + a WebSocket stream + /demo.

Reference wiring — verify the FastMCP http_app/lifespan API against the installed
version (see gofastmcp.com/deployment/http). The streamable-HTTP app MUST share its
lifespan with FastAPI or the MCP session manager won't initialise.
"""
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.mcp_server import mcp
from backend.agent.orchestrator import run_demo

mcp_app = mcp.http_app(path="/")
app = FastAPI(lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# Minimal single-session event bus for the demo. For multi-client, key queues per connection.
_queue: "asyncio.Queue[dict]" = asyncio.Queue()


async def _emit(event: dict) -> None:
    await _queue.put(event)


@app.post("/demo")
async def demo() -> dict:
    """Kick off the canonical scenario; events stream over /ws."""
    asyncio.create_task(run_demo(_emit))
    return {"started": True}


@app.websocket("/ws")
async def ws(sock: WebSocket) -> None:
    await sock.accept()
    try:
        while True:
            event = await _queue.get()
            await sock.send_json(event)
    except WebSocketDisconnect:
        return
