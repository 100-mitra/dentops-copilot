# Run the MCP server in Claude Desktop (the cold-email flex)

The same FastMCP server runs over stdio for Claude Desktop. Add this to
`claude_desktop_config.json` (Claude Desktop → Settings → Developer → Edit config),
then restart Claude Desktop. The `dentops` tools, resources, and prompts will appear.

```json
{
  "mcpServers": {
    "dentops": {
      "command": "python",
      "args": ["-m", "backend.mcp_server"],
      "cwd": "/absolute/path/to/dentops-copilot",
      "env": { "DATABASE_URL": "sqlite:///./dentops.db" }
    }
  }
}
```

Notes:
- Use an absolute `cwd`, and a Python that has the deps installed (point `command` at your venv's python if needed, e.g. `/abs/path/.venv/bin/python`).
- Verify the exact config schema for your Claude Desktop version.
- This is a portfolio tool with mock data — not for real patient use.
