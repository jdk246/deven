# trust-trace Backend API Contract

This document is the handoff contract for:

- Frontend teammate
- Telegram integration
- External API consumers
- Demo reviewers

Base URL examples below assume the backend is running at `http://127.0.0.1:8000`.

## `GET /health`

Purpose:
Return a simple backend liveness check.

Method:
`GET`

Path:
`/health`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "status": "ok"
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/health"
```

Frontend usage notes:
Use this for a top-level service heartbeat only. It does not report data readiness.

## `GET /api/agent/health`

Purpose:
Return agent-mode status for the backend API.

Method:
`GET`

Path:
`/api/agent/health`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "status": "ok",
  "agent_mode": "deterministic",
  "data_mode": "seed",
  "openai_ready": false
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/agent/health"
```

Frontend usage notes:
Show this in admin/debug surfaces when you need to know whether OpenAI mode is configured and ready.

## `GET /api/agent/tools`

Purpose:
List the registered agent tools the backend can call.

Method:
`GET`

Path:
`/api/agent/tools`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "items": [
    {
      "name": "crypto_market_rank",
      "category": "binance_skill",
      "description": "Fetch current Binance trending-token rank or smart-money inflow rank data.",
      "input_schema": {},
      "output_schema": {}
    }
  ]
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/agent/tools"
```

Frontend usage notes:
Good for admin/debug views and for any client that wants to inspect available capabilities before calling the agent.

## `GET /api/agent/examples`

Purpose:
Return example requests external clients can use when integrating with the agent API.

Method:
`GET`

Path:
`/api/agent/examples`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "items": [
    {
      "title": "Trending Tokens",
      "description": "Ask the agent for the strongest current token attention across tracked chains.",
      "endpoint": "/api/agent/query",
      "method": "POST",
      "request_body": {
        "message": "Which tokens are trending right now?",
        "debug": true
      },
      "expected_response_shape": {
        "answer": "string",
        "evidence_used": "list<object>",
        "missing_data": "list<string>",
        "tool_trace": "list<object>",
        "disclaimer": "string"
      }
    }
  ]
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/agent/examples"
```

Frontend usage notes:
Use this to seed quick-start prompts, onboarding examples, or external API docs.

## `POST /api/agent/query`

Purpose:
Ask the core market-intelligence agent a question.

Method:
`POST`

Path:
`/api/agent/query`

Query params:
None.

Request body:

```json
{
  "message": "Why is BNB trending?",
  "chain_id": "56",
  "token_context": {
    "chain_id": "56",
    "contract_address": "0x...",
    "symbol": "BNB",
    "name": "BNB"
  },
  "debug": true
}
```

Response shape:

```json
{
  "answer": "string",
  "evidence_used": [
    {
      "type": "string",
      "status": "ok"
    }
  ],
  "missing_data": ["string"],
  "tool_trace": [
    {
      "tool_name": "string",
      "registry_name": "string",
      "source": "string",
      "status": "ok"
    }
  ],
  "disclaimer": "string"
}
```

Curl example:

```bash
curl -sS \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"Why is BNB trending?","chain_id":"56","debug":true}' \
  "http://127.0.0.1:8000/api/agent/query"
```

Frontend usage notes:
This is the main product API. The frontend and Telegram client should both call this endpoint instead of querying Binance or the database directly.

## `GET /api/tokens/trending`

Purpose:
Return the locally tracked trending-token list with chain metadata and current stored scores.

Method:
`GET`

Path:
`/api/tokens/trending`

Query params:

- `chain_id` (optional)
- `limit` (optional, default `30`, max `100`)

Request body:
None.

Response shape:

```json
{
  "items": [
    {
      "chain_id": "56",
      "chain_name": "BNB Chain",
      "chain_short_name": "BSC",
      "contract_address": "0x...",
      "symbol": "BNB",
      "name": "BNB",
      "icon_url": "https://...",
      "price": 650.0,
      "percent_change_24h": 4.1,
      "volume_24h": 2500000.0,
      "liquidity": 1900000.0,
      "holders": 40000,
      "risk_level_enum": "LOW",
      "kol_mention_count": 4,
      "smart_money_signal_count": 3,
      "attention_score": 82.0,
      "label": "Watchlist",
      "updated_at": "2026-04-26T00:00:00Z"
    }
  ],
  "available_chains": []
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/tokens/trending?chain_id=56&limit=10"
```

Frontend usage notes:
Use this for token tables and chain-filtered overview pages.

## `GET /api/tokens/{chain_id}/{contract_address}`

Purpose:
Return a detailed token view with local market, audit, social, smart-money, and insight context.

Method:
`GET`

Path:
`/api/tokens/{chain_id}/{contract_address}`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "token": {},
  "latest_market": {},
  "audit": {},
  "smart_money_signals": [],
  "kol_mentions": [],
  "insight": {},
  "source_freshness": {
    "market_snapshot_at": "2026-04-26T00:00:00Z",
    "audit_at": "2026-04-26T00:00:00Z",
    "latest_smart_money_at": "2026-04-26T00:00:00Z",
    "latest_kol_post_at": "2026-04-26T00:00:00Z",
    "insight_at": "2026-04-26T00:00:00Z",
    "kol_data_mode": "seed"
  }
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/tokens/56/0x0000000000000000000000000000000000000000"
```

Frontend usage notes:
Use this for token detail pages. It is the frontend-friendly aggregate payload.

## `GET /api/kols`

Purpose:
Return tracked KOL profiles with counts useful for overview lists.

Method:
`GET`

Path:
`/api/kols`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "data_mode": "seed",
  "items": [
    {
      "handle": "macro_mina",
      "display_name": "Macro Mina",
      "category": "macro",
      "priority": 1,
      "post_count": 2,
      "resolved_mention_count": 4,
      "wallet_count": 1
    }
  ]
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/kols"
```

Frontend usage notes:
Use this for KOL directory pages and filters. The payload is intentionally lightweight.

## `GET /api/kols/{handle}`

Purpose:
Return one KOL profile, recent posts, wallet metadata, and extracted mentions.

Method:
`GET`

Path:
`/api/kols/{handle}`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "profile": {},
  "wallets": [],
  "recent_posts": [],
  "mentions": []
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/kols/macro_mina"
```

Frontend usage notes:
Use this for KOL profile detail views. Handles may be passed with or without `@` on the caller side, but the API path itself should use the normalized handle string.

## `GET /api/insights`

Purpose:
Return the latest stored deterministic insight summaries for tracked tokens.

Method:
`GET`

Path:
`/api/insights`

Query params:

- `chain_id` (optional)
- `limit` (optional, default `20`, max `100`)

Request body:
None.

Response shape:

```json
{
  "items": [
    {
      "chain_id": "56",
      "chain_name": "BNB Chain",
      "contract_address": "0x...",
      "symbol": "BNB",
      "name": "BNB",
      "market_score": 74.0,
      "kol_score": 72.0,
      "smart_money_score": 66.0,
      "safety_score": 81.0,
      "final_score": 78.0,
      "attention_score": 78.0,
      "label": "Watchlist",
      "summary": "string",
      "updated_at": "2026-04-26T00:00:00Z"
    }
  ]
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/insights?chain_id=56&limit=10"
```

Frontend usage notes:
Use this for insight feeds, summary panels, and cross-token comparison views.

## `GET /api/admin/validate`

Purpose:
Check whether the backend has enough demo data loaded.

Method:
`GET`

Path:
`/api/admin/validate`

Query params:
None.

Request body:
None.

Response shape:

```json
{
  "status": "pass",
  "checks": [
    {
      "name": "kol_profiles",
      "status": "pass",
      "expected": 20,
      "actual": 20,
      "fix_hint": "Run POST /api/admin/refresh with the `kols` job."
    }
  ]
}
```

Curl example:

```bash
curl -sS "http://127.0.0.1:8000/api/admin/validate"
```

Frontend usage notes:
Use this in admin or demo-prep screens to surface readiness before presenting the product.

## `POST /api/admin/refresh`

Purpose:
Run backend ingestion jobs manually.

Method:
`POST`

Path:
`/api/admin/refresh`

Query params:
None.

Request body:

```json
{
  "jobs": ["market", "audits", "smart_money", "kols", "insights"],
  "chains": ["56", "CT_501"],
  "limit_per_chain": 20
}
```

Response shape:

```json
{
  "status": "ok",
  "jobs": [],
  "chains": [],
  "limit_per_chain": 20,
  "summary": [],
  "kol_summary": {},
  "insight_summary": {},
  "errors": []
}
```

Curl example:

```bash
curl -sS \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jobs":["market","audits","smart_money","kols","insights"],"chains":["56","CT_501"],"limit_per_chain":20}' \
  "http://127.0.0.1:8000/api/admin/refresh"
```

Frontend usage notes:
Keep this behind an admin-only control. It is useful for demo prep and manual refresh actions, but it is not a public-user workflow.
