# Deploy guide

The app = a Python API (FastAPI + FastMCP + WebSocket) + a static React frontend + Postgres. The agent calls the Anthropic API (paid per token — keep the key server-side).

## 0. Prereqs
- An `ANTHROPIC_API_KEY`.
- The repo pushed to GitHub.
- Accounts on a backend host (Render/Railway/Fly) and a static host (Vercel/Netlify). Free tiers work; note Render free instances sleep when idle.

## 1. Run locally first
```bash
cp .env.example .env        # add ANTHROPIC_API_KEY
make install
make seed
make api                    # terminal 1 -> http://localhost:8000  (check /health)
make web                    # terminal 2 -> http://localhost:5173
```
Or `docker compose up` (starts Postgres + API; run `make seed` once).

## 2. Deploy the backend (pick one)
Any host that supports **WebSockets** and Docker.

- Render: New → Blueprint → select the repo (uses `render.yaml`; provisions Postgres). In the service settings add `ANTHROPIC_API_KEY` as a secret. After first deploy, open a shell and run `python -m backend.db.seed` once.
- Railway: New project from repo → add the Postgres plugin (sets `DATABASE_URL`) → set `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`. Run the seed once.
- Fly.io: `fly launch` (uses the Dockerfile) → `fly secrets set ANTHROPIC_API_KEY=...` → attach Postgres.

Note your backend URL, e.g. `https://dentops-api.onrender.com`.

## 3. Deploy the frontend
- Vercel: import the repo, set root to `frontend/`, build `npm run build`, output `dist`.
- Set env `VITE_WS_URL = wss://<your-backend-domain>/ws` (note `wss://`, not `ws://`).

## 4. Two things to wire (TODO in code)
- CORS: add `CORSMiddleware` in `backend/app.py` allowing your frontend origin.
- The `/ws` event bus in `app.py` is single-session for the demo; for multiple viewers key the queue per connection.

## 5. Verify
`GET /health` returns `{"ok": true}` → open the frontend → "Run demo · patient #1042" → steps stream in and drafts populate.

## Cost & safety
Each demo run makes real (paid) Anthropic calls — cheap, not free. Never commit `.env`. Mock data only; not for real patient data.
