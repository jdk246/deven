Here is the updated repo-ready `REQUIREMENTS.md`, rewritten around the **agent-first backend architecture**. I kept Binance Skills as callable agent tools because Binance Skills Hub is designed for agents and custom stacks, including LangChain/CrewAI/custom frameworks, and Binance’s token-info skill exposes the market/token data we need. ([GitHub][1]) I also kept OpenAI as an optional upgrade path because the OpenAI Agents SDK supports function tools / tool calling, which maps cleanly to your new `agent_tools` layer. ([OpenAI Developers][2])

---

# HypeCheck Agent API — Requirements Document

## 1. Project Summary

HypeCheck is an **AI market-intelligence agent API** for crypto research.

The core product is not the frontend dashboard. The core product is an **agent backend** that external clients can call. The React website, Telegram bot, and any future integrations are simply example clients of the same agent API.

The agent uses:

1. **Binance Skills tools** for live market, token, audit, smart-money, and wallet data.
2. **Internal database context tools** for Twitter/X KOL posts, seed KOL data, extracted token mentions, sentiment, cached insights, and optional wallet evidence.
3. **An agent orchestrator** that chooses which tools to call and returns source-backed answers.
4. **A public API** that external clients can integrate with.

The hackathon narrative is:

> HypeCheck is an AI agent that separates crypto hype from evidence by combining Binance Skills market intelligence with curated Twitter/X KOL context and explainable tool traces.

The system is for **market research only** and must not provide financial advice.

---

## 2. Current Implementation State

The backend has already completed the original chunks up to **Chunk 14**.

That means the project should already have:

```txt
FastAPI backend
SQLite / SQLAlchemy database
BinanceSkillsClient HTTP client
Binance market ingestion
KOL seed data
KOL ingestion
Token extraction
Sentiment classification
Token mapping
Scoring system
Insight generation
Backend API routes
Basic deterministic chatbot
```

An additional agent-tool abstraction has also been added after Chunk 14.

This means the backend should now include:

```txt
backend/app/agent_tools/binance_skill_tools.py
backend/app/schemas.py or equivalent AgentToolResult schema
Updated chat_agent.py using Binance tool functions
```

The required Binance Skill tool functions are:

```txt
crypto_market_rank
query_token_info
query_token_audit
trading_signal
query_address_info
```

Each tool result must include:

```txt
skill_name
tool_name
input_args
source
status
latency_ms
fetched_at
data
```

The goal from this point onward is **not frontend development**. A teammate will build the frontend separately. Backend work should focus on:

```txt
Agent API surface
Tool registry
Internal database context tools
Agent orchestration
Backend validation
Testing
API contract documentation
Demo-readiness scripts
Optional OpenAI mode
Optional OpenClaw adapter
Optional Telegram/API integration support
```

---

## 3. Product Positioning

### 3.1 Primary Product

The primary product is:

```txt
A Binance Skills-powered AI market intelligence agent exposed through an API.
```

The agent can be used by:

```txt
React frontend
Telegram bot
External apps
Other hackathon teams
CLI scripts
Future mobile clients
```

### 3.2 Example Clients

The frontend website should be described as:

```txt
An example client that demonstrates how to consume the HypeCheck Agent API.
```

Telegram integration should be described as:

```txt
An optional example integration that sends user questions to the same agent API.
```

### 3.3 Core Pitch

```txt
Most crypto dashboards show price and hype. HypeCheck gives users an agent that asks whether the hype is supported by Binance Skills market data, token risk checks, smart-money signals, and curated Twitter/X KOL context.
```

### 3.4 One-Liner

```txt
HypeCheck separates crypto hype from evidence.
```

---

## 4. Architecture

## 4.1 High-Level Architecture

```txt
External Clients
  - React dashboard
  - Telegram bot
  - External API consumers
        │
        ▼
Public Agent API
  - POST /api/agent/query
  - GET  /api/agent/tools
  - GET  /api/agent/examples
  - GET  /api/agent/health
        │
        ▼
Agent Orchestrator
  - Classifies user intent
  - Selects tools
  - Executes tool plan
  - Synthesizes answer
  - Returns evidence and tool trace
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
Binance Skills Tools                  Internal Context Tools
  - crypto_market_rank                  - get_trending_token_context
  - query_token_info                    - get_token_context
  - query_token_audit                   - search_kol_mentions
  - trading_signal                      - get_kol_summary
  - query_address_info                  - get_latest_insight
                                        - get_high_risk_tokens
                                        - get_data_mode_status
        │                                      │
        ▼                                      ▼
BinanceSkillsClient                    SQLite / Postgres DB
  - HTTP calls to Binance                 - KOL posts
  - normalized tool result                - mentions
  - latency tracking                      - sentiment
  - raw JSON preserved                    - cached snapshots
                                           - insights
                                           - agent run logs
```

---

## 4.2 Agent-Controlled Data Access

The agent should not directly perform arbitrary HTTP requests.

Instead:

```txt
Agent → ToolRegistry → Binance Skill Tool → BinanceSkillsClient → Binance endpoint
```

The agent should not directly query SQL tables.

Instead:

```txt
Agent → ToolRegistry → Internal Context Tool → database query
```

This makes the system clearly agent/tool-based rather than a normal backend API wrapper.

---

## 4.3 Required Tool Families

### Binance Skill Tools

These tools call Binance Skills through the existing backend client.

```txt
crypto_market_rank
query_token_info
query_token_audit
trading_signal
query_address_info
```

### Internal Context Tools

These tools read from our local database.

```txt
get_trending_token_context
get_token_context
search_kol_mentions
get_kol_summary
get_latest_insight
get_high_risk_tokens
get_data_mode_status
```

### Optional Future Tools

```txt
twitter_recent_search
openai_summary_tool
telegram_send_message
portfolio_context_tool
```

These are not required for the hackathon MVP.

---

## 5. Technical Stack

## 5.1 Backend

```txt
Language: Python 3.11+
Framework: FastAPI
HTTP client: httpx
Database: SQLite for local demo
ORM: SQLAlchemy
Validation: Pydantic
Testing: pytest
Config: pydantic-settings or python-dotenv
```

## 5.2 Optional AI Layer

Default mode:

```txt
Deterministic agent orchestrator
```

Optional mode:

```txt
OpenAI-powered agent using the same ToolRegistry
```

Environment variable:

```bash
AGENT_MODE=deterministic
```

Allowed values:

```txt
deterministic
openai
```

`deterministic` must remain the default because the demo should work without an LLM key.

## 5.3 Optional OpenClaw Layer

OpenClaw may be used as an adapter, but it should not replace the backend agent.

Preferred relationship:

```txt
OpenClaw skill → HypeCheck Agent API → ToolRegistry → Binance Skill Tools + DB Context Tools
```

Do not duplicate Binance logic inside the OpenClaw adapter.

---

## 6. Local Development Requirements

Everything should be buildable from VSCode.

Required local tools:

```txt
Python 3.11+
Node.js 20+ only if running frontend locally
npm only if running frontend locally
Git
SQLite
Docker Desktop optional
```

Required backend setup:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend should run at:

```txt
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Agent health check:

```bash
curl http://localhost:8000/api/agent/health
```

---

## 7. Environment Variables

Create or update `.env.example`.

```bash
# App
ENVIRONMENT=development
DATABASE_URL=sqlite:///./app.db
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Binance
BINANCE_REQUEST_TIMEOUT_SECONDS=20
BINANCE_MAX_RETRIES=2

# KOL data
# Options: seed, live
KOL_DATA_MODE=seed

# Optional X/Twitter API
X_BEARER_TOKEN=

# Agent
# Options: deterministic, openai
AGENT_MODE=deterministic

# Optional OpenAI
OPENAI_API_KEY=
LLM_MODEL=gpt-4.1-mini

# Ingestion
ENABLE_SCHEDULER=false
USE_DEMO_FALLBACKS=true
```

Rules:

```txt
Backend must work with KOL_DATA_MODE=seed.
Backend must work with AGENT_MODE=deterministic.
Backend must not require OPENAI_API_KEY for demo.
Backend must not require X_BEARER_TOKEN for demo.
```

---

## 8. Data Requirements

## 8.1 KOL Profiles

File:

```txt
backend/data/kols.yaml
```

Minimum requirements:

```txt
At least 20 KOL profiles
Each profile has handle
Each profile has display_name
Each profile has category
Each profile has priority
Wallets are optional
```

Example:

```yaml
- handle: "KOL_HANDLE_1"
  display_name: "KOL Display Name 1"
  category: "macro"
  priority: 1
  notes: "Optional internal note"
  wallets: []
```

Wallets may be included only if public evidence exists.

```yaml
wallets:
  - chain_id: "56"
    address: "0x0000000000000000000000000000000000000000"
    source_type: "public_claim"
    source_url: "https://x.com/example/status/..."
    confidence: 0.7
```

---

## 8.2 KOL Seed Posts

File:

```txt
backend/data/kol_posts_seed.json
```

Minimum requirements:

```txt
At least 40 seed posts
At least 10 KOLs represented
At least 15 posts with cashtags
At least 5 posts with clear bullish or bearish language
Each post has engagement metrics
Each post has source_mode="seed"
```

Required fields:

```txt
external_post_id
handle
created_at
text
url
like_count
repost_count
reply_count
view_count
source_mode
```

Example:

```json
{
  "external_post_id": "seed-001",
  "handle": "KOL_HANDLE_1",
  "created_at": "2026-04-25T08:00:00Z",
  "text": "$BNB ecosystem tokens are seeing strong volume today. Watching liquidity and holder concentration closely.",
  "url": "https://x.com/KOL_HANDLE_1/status/seed-001",
  "like_count": 1200,
  "repost_count": 250,
  "reply_count": 90,
  "view_count": 45000,
  "source_mode": "seed"
}
```

Important UI/API requirement:

```txt
If seed mode is active, responses must expose KOL data mode as seed/demo data.
```

---

## 8.3 Binance Data

The backend should ingest or fetch:

```txt
Trending tokens
Token metadata
Token dynamic market data
Token audit/risk data
Smart-money signals
Optional wallet/address positions
```

Supported P0 chains:

```txt
BSC: 56
Solana: CT_501
```

Optional P1 chain:

```txt
Base: 8453
```

---

## 9. Database Requirements

The backend should include these tables or equivalent SQLAlchemy models:

```txt
tokens
token_snapshots
token_audits
smart_money_signals
kol_profiles
kol_wallets
kol_posts
token_mentions
kol_wallet_positions
token_insights
chat_logs
agent_runs
```

`agent_runs` may be a new table or an extension of `chat_logs`.

Required `agent_runs` fields:

```txt
id
request_id
created_at
user_message
normalized_intent
answer
evidence_json
missing_data_json
tool_trace_json
data_mode
total_latency_ms
status
```

The database must support a full demo flow using only:

```txt
Seed KOL data
Cached/ingested Binance data
Deterministic agent responses
```

---

## 10. Agent Tool Result Schema

Create or verify a Pydantic schema equivalent to:

```python
class AgentToolResult(BaseModel):
    skill_name: str
    tool_name: str
    input_args: dict
    source: str
    status: str
    latency_ms: float | None = None
    fetched_at: datetime
    data: dict | list | None = None
    error: str | None = None
```

Allowed `status` values:

```txt
success
empty
error
partial
cached
```

Rules:

```txt
Every agent tool must return AgentToolResult.
Tools must not return raw unwrapped dicts to the agent.
Tools must preserve enough metadata for debugging and demo traceability.
Tool failures should return status="error" instead of crashing the agent.
Empty database results should return status="empty" instead of crashing.
```

---

## 11. Binance Skill Tool Requirements

File:

```txt
backend/app/agent_tools/binance_skill_tools.py
```

Required functions:

```python
async def crypto_market_rank(...)
async def query_token_info(...)
async def query_token_audit(...)
async def trading_signal(...)
async def query_address_info(...)
```

Each function must:

```txt
Call the appropriate BinanceSkillsClient method
Return AgentToolResult
Include metadata
Normalize response shape where practical
Preserve raw or semi-raw Binance response under data
Measure latency_ms
Set fetched_at
Catch exceptions and return status="error"
```

Required metadata:

```txt
skill_name
tool_name
input_args
source
status
latency_ms
fetched_at
data
error
```

Example source values:

```txt
binance_skills.crypto-market-rank
binance_skills.query-token-info
binance_skills.query-token-audit
binance_skills.trading-signal
binance_skills.query-address-info
```

---

## 12. Internal Context Tool Requirements

File:

```txt
backend/app/agent_tools/database_context_tools.py
```

Required functions:

```python
async def get_trending_token_context(...)
async def get_token_context(...)
async def search_kol_mentions(...)
async def get_kol_summary(...)
async def get_latest_insight(...)
async def get_high_risk_tokens(...)
async def get_data_mode_status(...)
```

Each function must:

```txt
Read from the local database
Return AgentToolResult
Include same metadata shape as Binance tools
Return status="empty" when no rows match
Never crash on missing rows
Never call Binance directly
Never call the LLM directly
```

Purpose:

```txt
These tools give the agent access to local KOL, sentiment, cached insight, and demo data.
```

---

## 13. Tool Registry Requirements

File:

```txt
backend/app/agent_tools/registry.py
```

Create a central `ToolRegistry`.

Each registered tool should include:

```txt
name
description
input_schema
output_schema
category
callable
```

Allowed categories:

```txt
binance_skill
internal_context
optional_external
```

Required registry functions:

```python
def list_agent_tools() -> list[dict]:
    ...

async def call_tool(tool_name: str, input_args: dict) -> AgentToolResult:
    ...
```

Required registered tools:

```txt
crypto_market_rank
query_token_info
query_token_audit
trading_signal
query_address_info
get_trending_token_context
get_token_context
search_kol_mentions
get_kol_summary
get_latest_insight
get_high_risk_tokens
get_data_mode_status
```

Rules:

```txt
Agent orchestrator must call tools through ToolRegistry.
Agent orchestrator must not import tool functions directly.
GET /api/agent/tools must be powered by ToolRegistry.
```

---

## 14. Agent Orchestrator Requirements

File:

```txt
backend/app/services/chat_agent.py
```

The current chatbot should be refactored into an **agent orchestrator**.

Default mode:

```txt
deterministic
```

Supported intents:

```txt
trending_tokens
token_explanation
kol_sentiment
high_risk_tokens
smart_money_activity
compare_tokens
general_help
```

The orchestrator should:

```txt
Receive user message
Classify intent
Build a tool plan
Execute tools via ToolRegistry
Synthesize answer
Return structured response
Log agent run
```

The orchestrator must not:

```txt
Give financial advice
Invent market data
Say "buy"
Say "sell"
Say "guaranteed"
Say "safe"
```

Allowed wording:

```txt
elevated attention
market signal
social signal
risk signal
smart-money signal
evidence suggests
data is missing
not financial advice
```

---

## 15. Agent Response Schema

`POST /api/agent/query` must return:

```json
{
  "answer": "string",
  "evidence_used": [],
  "missing_data": [],
  "tool_trace": [],
  "disclaimer": "string"
}
```

When `debug=true`, include full tool trace.

When `debug=false`, include compact trace or evidence summary.

Required disclaimer:

```txt
This dashboard is for market research only and does not constitute financial advice. Always do your own research.
```

---

## 16. Public Agent API Requirements

Create router:

```txt
backend/app/routers/agent.py
```

Register it in:

```txt
backend/app/main.py
```

Required endpoints:

```txt
GET  /api/agent/health
GET  /api/agent/tools
GET  /api/agent/examples
POST /api/agent/query
```

---

## 16.1 GET /api/agent/health

Response:

```json
{
  "status": "ok",
  "agent_mode": "deterministic",
  "tool_registry_status": "ok"
}
```

---

## 16.2 GET /api/agent/tools

Response:

```json
{
  "tools": [
    {
      "name": "crypto_market_rank",
      "description": "Fetches token market rankings using Binance Skills.",
      "category": "binance_skill",
      "input_schema": {},
      "output_schema": {}
    }
  ]
}
```

---

## 16.3 GET /api/agent/examples

Response should include example external API calls.

Required examples:

```txt
Trending tokens
Why a token is trending
Risky tokens
KOL sentiment
Whether KOL hype is backed by market data
Smart-money activity
```

Example response item:

```json
{
  "title": "Ask why a token is trending",
  "method": "POST",
  "endpoint": "/api/agent/query",
  "request_body": {
    "message": "Why is BNB trending?",
    "debug": true
  },
  "expected_response_shape": {
    "answer": "string",
    "evidence_used": [],
    "missing_data": [],
    "tool_trace": [],
    "disclaimer": "string"
  }
}
```

---

## 16.4 POST /api/agent/query

Request:

```json
{
  "message": "Which tokens are trending and why?",
  "chain_id": "56",
  "token": null,
  "debug": true
}
```

Response:

```json
{
  "answer": "The strongest current signals are...",
  "evidence_used": [
    "crypto_market_rank returned trending token data",
    "get_trending_token_context returned local KOL context"
  ],
  "missing_data": [
    "No live Twitter/X data available; using seed KOL data"
  ],
  "tool_trace": [
    {
      "tool_name": "crypto_market_rank",
      "status": "success",
      "latency_ms": 421.5,
      "source": "binance_skills.crypto-market-rank"
    }
  ],
  "disclaimer": "This dashboard is for market research only and does not constitute financial advice. Always do your own research."
}
```

---

## 17. Backward Compatibility API

Keep existing route:

```txt
POST /api/chat
```

But make it call the same underlying agent service as:

```txt
POST /api/agent/query
```

This preserves frontend compatibility while making the agent API the main product.

---

## 18. Existing Backend API Requirements

These routes should continue to work for the frontend teammate:

```txt
GET  /health
GET  /api/tokens/trending
GET  /api/tokens/{chain_id}/{contract_address}
GET  /api/kols
GET  /api/kols/{handle}
GET  /api/insights
POST /api/admin/refresh
GET  /api/admin/validate
POST /api/agent/query
GET  /api/agent/tools
GET  /api/agent/examples
```

The frontend should primarily use:

```txt
GET  /api/tokens/trending
GET  /api/tokens/{chain_id}/{contract_address}
GET  /api/kols
GET  /api/insights
POST /api/agent/query
GET  /api/agent/tools
GET  /api/agent/examples
```

---

## 19. Admin Validation Endpoint

Create:

```txt
GET /api/admin/validate
```

This endpoint validates whether the backend has enough data for the demo.

Response:

```json
{
  "status": "pass",
  "checks": [
    {
      "name": "kol_profiles_count",
      "status": "pass",
      "expected": ">= 20",
      "actual": 20,
      "fix_hint": "Add more KOLs to backend/data/kols.yaml"
    }
  ]
}
```

Allowed overall statuses:

```txt
pass
warn
fail
```

Required checks:

```txt
kol_profiles_count >= 20
kol_posts_count >= 40
token_mentions_count >= 10
tokens_count >= 10
token_snapshots_count >= 10
token_audits_count >= 5
token_insights_count >= 5
agent_tools_registered_count >= 10
binance_skill_tools_registered_count >= 5
internal_context_tools_registered_count >= 6
```

Preferred additional checks:

```txt
at least one successful agent run
at least one successful Binance skill tool call
KOL_DATA_MODE is visible
AGENT_MODE is visible
```

---

## 20. Agent Run Logging

Every call to:

```txt
POST /api/agent/query
```

must create an agent run log.

Required fields:

```txt
request_id
created_at
user_message
normalized_intent
answer
evidence_json
missing_data_json
tool_trace_json
data_mode
total_latency_ms
status
```

Purpose:

```txt
Debugging
Demo tool trace
Proof of Binance Skill tool usage
Frontend evidence display
```

---

## 21. Backend Validation Script

Create:

```txt
backend/scripts/prepare_demo_backend.py
```

Responsibilities:

```txt
Load KOL profiles
Load seed KOL posts
Extract mentions
Classify sentiment
Map mentions where possible
Run market ingestion if network is available
Generate token insights
Run validation checks
Print final readiness report
```

Required flags:

```txt
--reset-db
--skip-network
```

Example commands:

```bash
cd backend
python scripts/prepare_demo_backend.py --reset-db
python scripts/prepare_demo_backend.py --skip-network
```

Expected output style:

```txt
KOL profiles: 20 PASS
Seed posts: 40 PASS
Mentions extracted: 25 PASS
Tokens ingested: 15 PASS
Insights generated: 10 PASS
Agent tools registered: 12 PASS
Demo backend status: READY
```

---

## 22. Backend Demo Script

Create:

```txt
backend/scripts/demo_agent_api.sh
```

The script should call:

```txt
GET  /health
GET  /api/agent/health
GET  /api/agent/tools
GET  /api/admin/validate
POST /api/agent/query
POST /api/agent/query
POST /api/agent/query
POST /api/agent/query
POST /api/agent/query
```

Required demo questions:

```txt
Which tokens are trending right now?
Which tokens have positive KOL sentiment?
Which trending tokens look risky?
Which tokens have smart-money activity?
Is the KOL hype backed by market data?
```

Run:

```bash
bash backend/scripts/demo_agent_api.sh
```

---

## 23. Testing Requirements

Testing is now the main priority after Chunk 14.

The backend must have tests for:

```txt
Seed data integrity
Token extraction and mapping
Scoring
Agent tools
Tool registry
Agent orchestrator
Backend end-to-end smoke flow
Optional live Binance integration
```

Normal test suite must not require internet access.

Live Binance tests must be optional and skipped unless explicitly enabled.

---

## 23.1 Seed Data Integrity Tests

File:

```txt
backend/tests/test_seed_data_integrity.py
```

Test requirements:

```txt
backend/data/kols.yaml exists
kols.yaml has at least 20 KOLs
Each KOL has handle
Each KOL has display_name
Each KOL has category
Each KOL has priority
backend/data/kol_posts_seed.json exists
kol_posts_seed.json has at least 40 posts
Each post has handle
Each post has created_at
Each post has text
Each post has url
Each post has like_count
Each post has repost_count
Each post has reply_count
Each post has view_count
Each post has source_mode="seed"
At least 15 posts contain cashtags
At least 5 posts contain bullish or bearish sentiment words
```

Run:

```bash
cd backend
pytest -q tests/test_seed_data_integrity.py
```

---

## 23.2 Token Extraction and Mapping Tests

File:

```txt
backend/tests/test_token_extraction_and_mapping.py
```

Test requirements:

```txt
Extracts EVM address
Rejects invalid EVM address
Extracts single cashtag
Extracts multiple cashtags
Handles no-mention text
Maps exact contract address
Maps cashtag to existing local token
Leaves duplicate symbol unresolved when no confidence signal exists
Chooses higher-liquidity token when duplicate symbol exists and liquidity is available
```

Run:

```bash
pytest -q tests/test_token_extraction_and_mapping.py
```

---

## 23.3 Scoring Tests

File:

```txt
backend/tests/test_scoring.py
```

Test requirements:

```txt
All scores stay between 0 and 100
High audit risk lowers safety_score
Audit unavailable lowers safety_score but does not crash
Bullish KOL mentions increase kol_score
Bearish KOL mentions reduce kol_score
High holder concentration penalizes market_score or safety_score
Missing market fields do not crash scoring
final_score is labeled Attention Score, not Buy Score
```

Run:

```bash
pytest -q tests/test_scoring.py
```

---

## 23.4 Agent Tool Tests

File:

```txt
backend/tests/test_agent_tools.py
```

Test requirements:

```txt
ToolRegistry lists all required tools
Every Binance skill tool returns AgentToolResult-compatible output
Every internal context tool returns AgentToolResult-compatible output
crypto_market_rank normalizes mocked Binance response
query_token_info normalizes mocked Binance response
query_token_audit normalizes mocked Binance response
trading_signal normalizes mocked Binance response
query_address_info normalizes mocked Binance response
Tool failures return status="error"
Empty DB context returns status="empty"
```

Mock `BinanceSkillsClient`.

Do not require internet.

Run:

```bash
pytest -q tests/test_agent_tools.py
```

---

## 23.5 Tool Registry Tests

File:

```txt
backend/tests/test_tool_registry.py
```

Test requirements:

```txt
Registry includes required Binance tools
Registry includes required internal context tools
list_agent_tools returns frontend/API-friendly metadata
call_tool executes a registered tool
call_tool rejects unknown tool names cleanly
Tool categories are correct
```

Run:

```bash
pytest -q tests/test_tool_registry.py
```

---

## 23.6 Agent Orchestrator Tests

File:

```txt
backend/tests/test_agent_orchestrator.py
```

Use mocked `ToolRegistry` calls.

Test these questions:

```txt
Which tokens are trending?
Why is BNB trending?
Which tokens look risky?
Which KOLs mentioned SOL?
Is the KOL hype backed by market data?
```

Each response must include:

```txt
answer
evidence_used
missing_data
tool_trace
disclaimer
```

Each test should assert that expected tools were called.

The agent must not produce:

```txt
buy recommendation
sell recommendation
guaranteed profit
safe token claim
```

Run:

```bash
pytest -q tests/test_agent_orchestrator.py
```

---

## 23.7 Backend End-to-End Smoke Test

File:

```txt
backend/tests/test_backend_e2e_smoke.py
```

Use FastAPI `TestClient` and temporary SQLite DB.

The test should run:

```txt
KOL seed ingestion
Token extraction
Sentiment classification
Scoring
Insight generation
Agent query
Validation endpoint
```

Test endpoints:

```txt
GET  /health
GET  /api/agent/health
GET  /api/agent/tools
GET  /api/admin/validate
POST /api/agent/query
GET  /api/kols
GET  /api/insights
```

No internet required.

Run:

```bash
pytest -q tests/test_backend_e2e_smoke.py
```

---

## 23.8 Optional Live Binance Integration Tests

File:

```txt
backend/tests/test_binance_live_integration.py
```

These tests must be skipped unless:

```bash
RUN_INTEGRATION_TESTS=true
```

Use pytest marker:

```txt
integration
```

Test requirements:

```txt
crypto_market_rank works against live Binance endpoint
query_token_info works for a token returned from rank response
query_token_audit works if a contract address is available
Tool result metadata is present
status is success, partial, or gracefully handled error
```

Run:

```bash
RUN_INTEGRATION_TESTS=true pytest -q -m integration
```

Normal tests must not depend on this.

---

## 24. API Contract Documentation

Create:

```txt
backend/API_CONTRACT.md
```

The document should describe:

```txt
GET  /health
GET  /api/agent/health
GET  /api/agent/tools
GET  /api/agent/examples
POST /api/agent/query
GET  /api/tokens/trending
GET  /api/tokens/{chain_id}/{contract_address}
GET  /api/kols
GET  /api/kols/{handle}
GET  /api/insights
GET  /api/admin/validate
POST /api/admin/refresh
```

For each endpoint include:

```txt
Purpose
Method
Path
Query params
Request body
Response shape
Curl example
Frontend usage notes
```

This file is the handoff contract for:

```txt
Frontend teammate
Telegram integration
External API consumers
Demo reviewers
```

---

## 25. Optional OpenAI Agent Mode

Only build this after deterministic mode and tests pass.

Create:

```txt
backend/app/services/openai_agent.py
```

Environment variable:

```bash
AGENT_MODE=openai
```

Requirements:

```txt
Use same ToolRegistry
Expose same response schema as deterministic mode
Fallback to deterministic mode if OpenAI fails
Do not invent market data
Do not provide financial advice
Do not use buy/sell recommendation language
Preserve tool_trace
```

The OpenAI agent may improve natural language flexibility, but it must not become required for the demo.

Default remains:

```bash
AGENT_MODE=deterministic
```

---

## 26. Optional OpenClaw Adapter

Only build this after backend API and tests are stable.

Create:

```txt
skills/hypecheck-agent/SKILL.md
```

The OpenClaw skill should describe how OpenClaw can call:

```txt
POST /api/agent/query
GET  /api/agent/tools
GET  /api/agent/examples
```

It should not duplicate Binance logic.

Correct architecture:

```txt
OpenClaw
  → HypeCheck Agent API
    → ToolRegistry
      → Binance Skill Tools
      → Internal Context Tools
```

Purpose:

```txt
Shows compatibility with an agent skill framework while keeping our backend as source of truth.
```

---

## 27. Optional Telegram Integration

Only build after the backend agent API is stable.

Telegram bot behavior:

```txt
User sends message
Telegram bot calls POST /api/agent/query
Telegram bot returns answer + compact evidence + disclaimer
```

Telegram should not call Binance directly.

Telegram should not query the database directly.

Telegram is only an example client.

---

## 28. Safety and Compliance Requirements

The system must never say:

```txt
You should buy this
You should sell this
Guaranteed profit
Guaranteed safe
This will pump
This is risk-free
```

Use safer wording:

```txt
The available evidence suggests elevated attention
The market signal is mixed
KOL data is positive but seed-based
Audit data shows high risk
Smart-money evidence is missing
This is market research only
```

Required disclaimer:

```txt
This dashboard is for market research only and does not constitute financial advice. Always do your own research.
```

Audit wording:

```txt
Lower risk detected
Medium risk
High risk
Audit unavailable
```

Do not use:

```txt
Safe
Approved
Guaranteed
```

---

## 29. Definition of Done

Backend is ready when:

```txt
FastAPI starts locally
GET /health works
GET /api/agent/health works
GET /api/agent/tools lists tools
POST /api/agent/query works
GET /api/admin/validate returns pass or warn, not fail
Seed KOL data loads
Token mentions are extracted
At least 10 Binance tokens are ingested or available from cached/demo flow
At least 5 token insights exist
Agent responses include tool_trace
Agent responses include disclaimer
Tests pass without internet
Live Binance integration test can be run optionally
API_CONTRACT.md exists
demo_agent_api.sh exists
prepare_demo_backend.py exists
```

---

## 30. Backend Build Order From Current State

Since chunks 1–14 and the Binance tool abstraction have already been built, continue in this order:

```txt
15. Agent API surface
16. Internal database context tools
17. Tool registry
18. Deterministic agent orchestrator
19. Agent run logging
20. Backend data validation endpoint
21. Seed data integrity tests
22. Token extraction and mapping tests
23. Scoring tests
24. Agent tool tests
25. Tool registry tests
26. Agent orchestrator tests
27. Backend E2E smoke test
28. Optional live Binance integration tests
29. Demo data readiness script
30. Public API examples endpoint
31. API contract document
32. Backend demo script
33. Optional OpenAI agent mode
34. Optional OpenClaw adapter
35. Optional Telegram integration
```

---

# Codex Chunk Prompts

## Chunk 15 — Agent API Surface

Create a new FastAPI router at `backend/app/routers/agent.py`. Add `GET /api/agent/health`, `GET /api/agent/tools`, `GET /api/agent/examples`, and `POST /api/agent/query`. The query endpoint should accept a user message, optional `chain_id`, optional token context, and optional `debug` boolean. It should call the existing agent/chat service and return `answer`, `evidence_used`, `missing_data`, `tool_trace`, and `disclaimer`. Keep `POST /api/chat` as a backward-compatible alias that calls the same service. Register the agent router in `main.py`.

---

## Chunk 16 — Internal Database Context Tools

Create `backend/app/agent_tools/database_context_tools.py`. Add async internal tool functions returning `AgentToolResult`: `get_trending_token_context`, `get_token_context`, `search_kol_mentions`, `get_kol_summary`, `get_latest_insight`, `get_high_risk_tokens`, and `get_data_mode_status`. These tools should read only from the database, not Binance and not the LLM. They should include metadata fields matching the Binance tools: `skill_name`, `tool_name`, `input_args`, `source`, `status`, `latency_ms`, `fetched_at`, and `data`. Empty results should return `status="empty"` instead of crashing.

---

## Chunk 17 — Tool Registry

Create `backend/app/agent_tools/registry.py`. Implement a central `ToolRegistry` that registers all Binance skill tools and all internal database context tools. Each registered tool should have name, description, input schema, output schema, category, and callable. Categories should include `binance_skill` and `internal_context`. Add `list_agent_tools()` and `call_tool(tool_name, input_args)`. Refactor the agent/chat service so it calls all tools through the registry instead of importing individual tool functions directly.

---

## Chunk 18 — Deterministic Agent Orchestrator

Refactor `backend/app/services/chat_agent.py` into a deterministic agent orchestrator. It should classify user messages into simple intents: `trending_tokens`, `token_explanation`, `kol_sentiment`, `high_risk_tokens`, `smart_money_activity`, `compare_tokens`, and `general_help`. For each intent, build a small tool plan, call tools through `ToolRegistry`, and synthesize a structured answer. For trending questions, call `crypto_market_rank` and `get_trending_token_context`. For token explanation questions, call `query_token_info`, `query_token_audit`, `search_kol_mentions`, and `get_latest_insight` when token identifiers are available. For risky token questions, call `get_high_risk_tokens`. For KOL questions, call `search_kol_mentions` and `get_kol_summary`. Every response must include `answer`, `evidence_used`, `missing_data`, `tool_trace`, and the financial disclaimer.

---

## Chunk 19 — Agent Run Logging

Add agent run logging. Either extend `chat_logs` or create a new `agent_runs` table. Store `request_id`, `created_at`, `user_message`, `normalized_intent`, `answer`, `evidence_json`, `missing_data_json`, `tool_trace_json`, `data_mode`, `total_latency_ms`, and `status`. Every `POST /api/agent/query` call should write one row. When `debug=true`, the API response should include full `tool_trace`. When `debug=false`, it should include a compact evidence summary.

---

## Chunk 20 — Backend Data Validation Endpoint

Create `backend/app/services/backend_validation.py` and add `GET /api/admin/validate`. This endpoint should validate whether the backend has enough data for the demo. It should check: at least 20 KOL profiles, at least 40 KOL posts, at least 10 extracted token mentions, at least 10 ingested tokens, at least 10 token snapshots, at least 5 token audits, at least 5 generated token insights, at least 10 registered agent tools, at least 5 registered Binance skill tools, and at least 6 registered internal context tools. Return `status` as `pass`, `warn`, or `fail`, plus a list of checks with `name`, `status`, `expected`, `actual`, and `fix_hint`.

---

## Chunk 21 — Seed Data Integrity Tests

Add `backend/tests/test_seed_data_integrity.py`. Test that `backend/data/kols.yaml` exists, contains at least 20 KOLs, and each KOL has `handle`, `display_name`, `category`, and `priority`. Test that `backend/data/kol_posts_seed.json` exists, contains at least 40 posts, and each post has `handle`, `created_at`, `text`, `url`, `like_count`, `repost_count`, `reply_count`, `view_count`, and `source_mode="seed"`. Test that at least 15 seed posts contain cashtags and at least 5 contain bullish or bearish sentiment words. These tests must not require internet access.

---

## Chunk 22 — Token Extraction and Mapping Tests

Add `backend/tests/test_token_extraction_and_mapping.py`. Test EVM address extraction, invalid EVM address rejection, single cashtag extraction, multiple cashtag extraction, and no-mention handling. Add mapping tests using an in-memory SQLite database. Test exact contract address mapping, cashtag mapping to existing local tokens, duplicate-symbol unresolved behavior, and duplicate-symbol resolution by higher liquidity or volume when available. These tests must not require Binance network calls.

---

## Chunk 23 — Scoring Tests

Add `backend/tests/test_scoring.py`. Test that all scores stay between 0 and 100. Test that high audit risk lowers `safety_score`. Test that unavailable audit data lowers `safety_score` but does not crash. Test that bullish KOL mentions increase `kol_score`. Test that bearish KOL mentions reduce `kol_score`. Test that high holder concentration penalizes market or safety score. Test that missing market fields do not crash scoring. Test that final score is labeled `Attention Score` and never `Buy Score`.

---

## Chunk 24 — Agent Tool Tests

Add `backend/tests/test_agent_tools.py`. Mock `BinanceSkillsClient` responses so tests do not require internet access. Test that every Binance skill tool returns an `AgentToolResult`-compatible object with `skill_name`, `tool_name`, `input_args`, `source`, `status`, `latency_ms`, `fetched_at`, and `data`. Test `crypto_market_rank`, `query_token_info`, `query_token_audit`, `trading_signal`, and `query_address_info`. Test that internal database context tools return `status="empty"` instead of crashing when there are no matching rows.

---

## Chunk 25 — Tool Registry Tests

Add `backend/tests/test_tool_registry.py`. Test that the registry includes all required Binance tools and all required internal context tools. Test that `list_agent_tools()` returns API-friendly metadata. Test that `call_tool()` executes a registered tool. Test that unknown tool names fail cleanly. Test that tool categories are correct.

---

## Chunk 26 — Agent Orchestrator Tests

Add `backend/tests/test_agent_orchestrator.py`. Use mocked `ToolRegistry` calls. Test at least five questions: `Which tokens are trending?`, `Why is BNB trending?`, `Which tokens look risky?`, `Which KOLs mentioned SOL?`, and `Is the KOL hype backed by market data?`. Each response should include `answer`, `evidence_used`, `missing_data`, `tool_trace`, and `disclaimer`. Each test should assert that at least one expected tool was called for the matching intent. The agent must not produce buy/sell recommendations.

---

## Chunk 27 — Backend End-to-End Smoke Test

Add `backend/tests/test_backend_e2e_smoke.py` using FastAPI `TestClient` and a temporary SQLite database. Run KOL seed ingestion, token extraction, sentiment classification, scoring, and insight generation with mocked Binance market data. Test `GET /health`, `GET /api/agent/health`, `GET /api/agent/tools`, `GET /api/admin/validate`, `POST /api/agent/query`, `GET /api/kols`, and `GET /api/insights`. Verify that a full local backend flow works without frontend and without internet access.

---

## Chunk 28 — Optional Live Binance Integration Tests

Add `backend/tests/test_binance_live_integration.py` with pytest marker `integration`. These tests should be skipped unless `RUN_INTEGRATION_TESTS=true`. The test should call `crypto_market_rank` for BSC or Solana, assert a graceful `AgentToolResult`, then call `query_token_info` and `query_token_audit` for a token returned from the rank response if contract data is available. These tests may hit real Binance endpoints but must not be required for normal CI.

---

## Chunk 29 — Demo Data Readiness Script

Create `backend/scripts/prepare_demo_backend.py`. The script should run the minimum backend data setup needed for the demo: load KOL profiles, load seed KOL posts, extract mentions, classify sentiment, map mentions where possible, run market ingestion if network is available, generate token insights, and print a validation report. It should use the existing services rather than duplicating logic. Add `--skip-network` and `--reset-db` flags.

---

## Chunk 30 — Public API Examples Endpoint

Implement or complete `GET /api/agent/examples`. Return a JSON object containing example requests external clients can use. Include examples for querying trending tokens, asking why a token is trending, asking for risky tokens, asking whether KOL hype is supported by market data, and asking for KOL mentions. Each example should include title, description, endpoint, method, request body, and expected response shape.

---

## Chunk 31 — API Contract Document

Create `backend/API_CONTRACT.md`. Document the backend endpoints the frontend and Telegram clients should use. Include `GET /api/agent/tools`, `POST /api/agent/query`, `GET /api/agent/examples`, `GET /api/tokens/trending`, `GET /api/tokens/{chain_id}/{contract_address}`, `GET /api/kols`, `GET /api/insights`, and `GET /api/admin/validate`. For each endpoint, include method, path, query params, request body, response fields, and one curl example.

---

## Chunk 32 — Backend Demo Script

Create `backend/scripts/demo_agent_api.sh`. The script should call `/health`, `/api/agent/health`, `/api/agent/tools`, `/api/admin/validate`, and then run five `POST /api/agent/query` examples with `debug=true`. The script should print clean section headers. Include questions about trending tokens, KOL sentiment, risky tokens, smart-money activity, and whether KOL hype is supported by market data.

---

## Chunk 33 — Optional OpenAI Agent Mode

Add optional OpenAI-based agent mode behind `AGENT_MODE=deterministic|openai`. Keep deterministic as the default. Create `backend/app/services/openai_agent.py`. Use the same `ToolRegistry` as function tools. The OpenAI agent should receive the user message, choose tools from the registry, execute tools server-side, and produce the same response schema as deterministic mode: `answer`, `evidence_used`, `missing_data`, `tool_trace`, and `disclaimer`. If `OPENAI_API_KEY` is missing or the OpenAI call fails, automatically fall back to deterministic mode.

---

## Chunk 34 — Optional OpenClaw Adapter (Not added for now)

Add an optional OpenClaw adapter without changing the core backend. Create `skills/hypecheck-agent/SKILL.md`. The skill should explain that OpenClaw can call the local HypeCheck Agent API at `POST /api/agent/query` and inspect tools at `GET /api/agent/tools`. Include example prompts and curl commands. Do not duplicate Binance skill logic inside this OpenClaw skill. The backend remains the source of truth.

---

## Chunk 35 — Optional Telegram Client

Add an optional Telegram bot client only after backend API is stable. The Telegram bot should receive a user message, call `POST /api/agent/query`, and send back the agent answer, compact evidence, and disclaimer. Telegram must not call Binance directly and must not query the database directly. It is only an example client for the HypeCheck Agent API.

---

## Final Demo Flow

Run:

```bash
cd backend
python scripts/prepare_demo_backend.py --reset-db
uvicorn app.main:app --reload
```

Then in another terminal:

```bash
bash backend/scripts/demo_agent_api.sh
```


[1]: https://github.com/binance/binance-skills-hub?utm_source=chatgpt.com "GitHub - binance/binance-skills-hub: Binance Skills Hub is an open ..."
[2]: https://developers.openai.com/api/docs/guides/agents?utm_source=chatgpt.com "Agents SDK | OpenAI API"
