from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent_tools.registry import ToolRegistry
from app.config import get_settings
from app.db import get_db
from app.schemas import (
    AgentExampleItem,
    AgentExamplesResponse,
    AgentHealthResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentToolDescriptor,
    AgentToolListResponse,
)
from app.services.openai_agent import OpenAIAgentService, get_agent_service

router = APIRouter(prefix="/api/agent", tags=["agent"])

EXPECTED_QUERY_RESPONSE_SHAPE = {
    "answer": "string",
    "evidence_used": "list<object>",
    "missing_data": "list<string>",
    "tool_trace": "list<object>",
    "disclaimer": "string",
}

AGENT_EXAMPLES = [
    AgentExampleItem(
        title="Trending Tokens",
        description="Ask the agent for the strongest current token attention across tracked chains.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "Which tokens are trending right now?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="Why A Token Is Trending",
        description="Explain why one token has attention using market, KOL, audit, and smart-money context.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "Why is BNB trending?", "chain_id": "56", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="Risky Tokens",
        description="Ask for locally tracked tokens that currently look higher risk.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "Which tokens look risky?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="KOL Hype Vs Market Data",
        description="Check whether KOL attention is supported by market context rather than only social noise.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "Is the KOL hype backed by market data?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="KOL Mentions",
        description="Ask which KOLs have mentioned a token or symbol in the stored dataset.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "Which KOLs mentioned SOL?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="KOL Rankings",
        description="Rank tracked KOLs by sample-size-adjusted historical alignment after bullish and bearish mentions.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "Which KOLs have the best track record?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="Explain A KOL Score",
        description="Explain why one KOL has a higher or lower historical alignment score.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "How has @willy_woo_demo performed?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
    AgentExampleItem(
        title="KOL Ranking Methodology",
        description="Ask how KOL rankings are computed and what their limitations are.",
        endpoint="/api/agent/query",
        method="POST",
        request_body={"message": "How do you calculate KOL rankings?", "debug": True},
        expected_response_shape=EXPECTED_QUERY_RESPONSE_SHAPE,
    ),
]


@router.get("/health", response_model=AgentHealthResponse)
def health() -> AgentHealthResponse:
    settings = get_settings()
    return AgentHealthResponse(
        agent_mode=settings.agent_mode,
        data_mode=settings.kol_data_mode,
        openai_ready=OpenAIAgentService.is_ready(settings),
    )


@router.get("/tools", response_model=AgentToolListResponse)
def list_tools() -> AgentToolListResponse:
    registry = ToolRegistry()
    items = [AgentToolDescriptor(**tool) for tool in registry.list_agent_tools()]
    return AgentToolListResponse(items=items)


@router.get("/examples", response_model=AgentExamplesResponse)
def examples() -> AgentExamplesResponse:
    return AgentExamplesResponse(items=AGENT_EXAMPLES)


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(
    payload: AgentQueryRequest,
    db: Session = Depends(get_db),
) -> AgentQueryResponse:
    response = get_agent_service(db).answer_question(
        message=payload.message,
        chain_id=payload.chain_id,
        token_context=payload.token_context.model_dump(exclude_none=True) if payload.token_context else None,
        debug=payload.debug,
    )
    return AgentQueryResponse(**response)
