"""Thin MCP client so the agent calls tools THROUGH the protocol (not direct imports).

Reference using the FastMCP Client. Verify the Client API + result shape against
the installed fastmcp version. For lower latency you may keep a single long-lived
session instead of opening one per call.
"""
from fastmcp import Client
from backend.config import MCP_HTTP_URL


async def list_tools():
    async with Client(MCP_HTTP_URL) as c:
        return await c.list_tools()


async def call_tool(name: str, arguments: dict):
    async with Client(MCP_HTTP_URL) as c:
        return await c.call_tool(name, arguments)
