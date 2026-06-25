# DentOps Copilot

[![CI](https://github.com/100-mitra/dentops-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/100-mitra/dentops-copilot/actions/workflows/ci.yml)

An **MCP-native agentic copilot** for a dental practice. Given a dental X-ray + a patient record, a Claude agent orchestrates several MCP tools to detect findings, pull history, draft a patient-friendly summary and an insurance pre-authorisation narrative, and propose a recall — streaming every step live to a React dashboard over WebSocket. The MCP server (FastAPI + FastMCP) is callable by any MCP client, including Claude Desktop.

> Portfolio prototype. **Not a medical device.** Every generated artifact is a **draft for dentist review.**

![DentOps Copilot — live demo: a Claude agent calls MCP tools and streams grounded drafts to the dashboard](docs/demo.gif)

## What I built vs. what's third-party

- **Mine:** the FastMCP server (tools / resources / prompts over JSON-RPC), the Claude agent that orchestrates them through an MCP client, the grounded draft generation, the real-time WebSocket UI, and the deploy setup.
- **Third-party / mock:** the imaging detector. It sits behind a `DetectorBackend` interface; the default `MockDetector` returns fixture findings. No model is trained here. Swap in an off-the-shelf detector via the interface.

## Quickstart

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY
make install
make seed
make dev                      # API (uvicorn) + frontend (vite)
# open the printed localhost URL, click "Run demo · patient #1042"
```

Architecture, tool contracts, and the event protocol are in `SPEC.md`. Build/finish notes for Claude Code are in `CLAUDE.md`. Deployment is in `docs/DEPLOY.md`.

## Limitations & safety

Mock patient data and fixture detector output. No clinical validity; outputs are drafts only and route low-confidence findings to a dentist. Do not use with real patient data.
