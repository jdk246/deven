# trust-trace

TrustTrace is a local-first monorepo for a market-intelligence demo product.

The backend is the core product surface:

- FastAPI API
- SQLite by default
- Binance Skills client and agent-tool wrappers
- token ingestion, audits, smart-money, insights, KOL ingestion, KOL performance
- deterministic agent mode
- optional OpenAI tool-calling agent mode

The frontend is a demo website that consumes the backend API.

## What Runs Locally

- Backend API: `http://127.0.0.1:8000`
- Frontend app: `http://127.0.0.1:5173`
- FastAPI docs: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

## Repo Layout

```txt
backend/
  app/
    agent_tools/
    clients/
    routers/
    services/
    config.py
    db.py
    main.py
    models.py
    schemas.py
  data/
  scripts/
  tests/
frontend/
  src/
    api/
    components/
    lib/
    pages/
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- PowerShell on Windows

## 1. Create Local Env

Copy the sample env file:

```powershell
Copy-Item .env.example .env
```

Important defaults in `.env.example`:

- `AGENT_MODE=deterministic`
- `KOL_DATA_MODE=seed`
- `ENABLED_CHAINS=56,CT_501`
- `DATABASE_URL=sqlite:///./backend/trust_trace.db`

Optional OpenAI settings:

- `AGENT_MODE=openai`
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-5-nano`
- `OPENAI_REQUEST_TIMEOUT_SECONDS=20`
- `OPENAI_MAX_TOTAL_SECONDS=30`
- `OPENAI_MAX_TOOL_ROUNDS=3`
- `OPENAI_MAX_RETRIES=0`

Notes:

- `seed` mode is the supported local KOL mode.
- Binance-backed market/audit/smart-money data still comes from the backend, not the frontend.
- Keep `.env` private.

## 2. Install Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run backend tests:

```powershell
python -m pytest -q
```

Expected result is the current backend suite passing, with one optional integration test skipped unless enabled.

## 3. Prepare Demo Data

For the full local demo setup, run:

```powershell
cd backend
python scripts/prepare_demo_backend.py --reset-db
```

What this does:

- recreates tables if `--reset-db` is used
- loads seeded KOL profiles and posts
- ingests Binance-backed market/audit/smart-money data for enabled chains
- adds a small Binance-backed majors watchlist alongside trending tokens so core assets like BNB, BTC, ETH, and SOL show up in the local demo
- generates token insights
- computes KOL historical alignment / track record scores
- runs backend validation

Useful flags:

```powershell
python scripts/prepare_demo_backend.py --reset-db --limit-per-chain 20
python scripts/prepare_demo_backend.py --reset-db --skip-network
```

Use `--skip-network` only if you want a mostly local seed-backed setup without live Binance refresh.

## 4. Start the Backend

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/agent/health | ConvertTo-Json -Depth 5
```

## 5. Start the Frontend

In a second terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Then open:

```txt
http://127.0.0.1:5173
```

If the browser does not open automatically, that is normal for the current Vite script.

## 6. Standard Local Demo Flow

Use this sequence from a fresh clone:

```powershell
Copy-Item .env.example .env
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/prepare_demo_backend.py --reset-db
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then in another terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

## 7. Enable OpenAI Agent Mode

By default, the backend runs in deterministic mode.

If you want the OpenAI agent in the middle of the tool loop:

1. Edit `.env`
2. Set:

```env
AGENT_MODE=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-nano
OPENAI_REQUEST_TIMEOUT_SECONDS=20
OPENAI_MAX_TOTAL_SECONDS=30
OPENAI_MAX_TOOL_ROUNDS=3
OPENAI_MAX_RETRIES=0
```

3. Restart the backend

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/agent/health | ConvertTo-Json -Depth 5
```

You should see:

- `"agent_mode": "openai"`
- `"openai_ready": true`

How the agent works:

- deterministic mode: backend classifies intent and runs predefined tool plans
- OpenAI mode: model receives the user prompt and chooses from registered tools through the backend tool registry
- Binance access still stays behind `BinanceSkillsClient` and the tool abstraction
- OpenAI mode now uses a lighter default model plus a bounded request timeout, capped tool rounds, and a total time budget so slow tool-planning runs fall back faster

## 8. Useful Local API Checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/admin/validate | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8000/api/agent/tools | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8000/api/agent/examples | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8000/api/tokens/trending?limit=5 | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8000/api/kols/rankings | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8000/api/insights?limit=5 | ConvertTo-Json -Depth 10
```

Agent query example:

```powershell
$body = @{
  message = "Which KOLs have the best track record?"
  debug = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/agent/query `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

## 9. Frontend Notes

The frontend is a demo client for the backend API.

Current useful surfaces:

- dashboard
- markets
- KOL leaderboard and KOL profile pages
- token detail pages
- chat assistant
- API docs tab for external/demo consumers

If the frontend loads but data panels fail, the backend is usually not running.

## 10. API Docs

There are two API documentation surfaces:

- website tab: `API Docs` inside the frontend
- FastAPI docs: `http://127.0.0.1:8000/docs`

Detailed API contract:

- [backend/API_CONTRACT.md](backend/API_CONTRACT.md)

## 11. Common Windows Troubleshooting

### Port 8000 already in use

If backend restart fails with a socket error:

```powershell
Get-NetTCPConnection -LocalPort 8000
```

Then stop the old process:

```powershell
Stop-Process -Id <PID> -Force
```

Then start uvicorn again.

### Port 5173 already in use

Stop the old frontend dev server with `Ctrl + C` in the terminal that launched it, or restart Vite on another port.

### Frontend changes not showing

Restart the Vite dev server and hard refresh the browser:

```txt
Ctrl + Shift + R
```

### Browser shows fetch failures

Usually means one of:

- backend is not running
- backend is on a different port
- `.env` or frontend API base URL points somewhere else

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 12. Docker Compose

Optional local stack:

```powershell
docker compose up
```

This starts:

- backend on `8000`
- frontend on `5173`

The local manual flow is still the most reliable way to debug quickly during development.

## 13. Demo Script

If you have a bash-compatible shell available:

```bash
bash backend/scripts/demo_agent_api.sh
```

That script exercises the public agent API with demo prompts, including KOL ranking questions.

## 14. Current Product Boundaries

Working locally today:

- multi-chain tracked token ingestion for BSC + Solana by default
- Binance-backed trending ingestion plus a small curated majors watchlist
- token snapshots, audits, smart-money signals
- seeded KOL pipeline
- token mention extraction and mapping
- token insights and Attention Score
- KOL historical alignment / track record scoring
- deterministic agent
- optional OpenAI tool-calling agent

Important limitations:

- KOL social data is seed-mode by default, not live X ingestion
- no auth / rate limiting / production hardening yet
- no arbitrary contract scan endpoint for any token in the world
- the public API is demo-usable, not production-ready
