from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal

from sqlalchemy.orm import Session

from app.agent_tools.binance_skill_tools import (
    crypto_market_rank,
    query_address_info,
    query_token_audit,
    query_token_info,
    trading_signal,
)
from app.agent_tools.database_context_tools import (
    get_data_mode_status,
    get_high_risk_tokens,
    get_kol_summary,
    get_latest_insight,
    get_token_context,
    get_trending_token_context,
    search_kol_mentions,
)
from app.clients import BinanceSkillsClient
from app.schemas import AgentToolResult

ToolCategory = Literal["binance_skill", "internal_context"]
ToolCallable = Callable[..., Awaitable[AgentToolResult]] | Callable[..., AgentToolResult]

_TOOL_OUTPUT_SCHEMA = {
    "type": "AgentToolResult",
    "fields": [
        "skill_name",
        "tool_name",
        "input_args",
        "source",
        "status",
        "latency_ms",
        "fetched_at",
        "data",
        "error",
    ],
}


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    category: ToolCategory
    callable: ToolCallable


class ToolRegistry:
    def __init__(
        self,
        *,
        db: Session | None = None,
        binance_client: BinanceSkillsClient | None = None,
    ) -> None:
        self.db = db
        self.binance_client = binance_client
        self._tools = {tool.name: tool for tool in _default_tool_definitions()}

    def list_agent_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "category": tool.category,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
            }
            for tool in self._tools.values()
        ]

    def get_tool(self, tool_name: str) -> RegisteredTool:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        return tool

    async def call_tool(
        self,
        tool_name: str,
        input_args: dict[str, Any] | None = None,
    ) -> AgentToolResult:
        tool = self.get_tool(tool_name)
        kwargs = dict(input_args or {})

        if tool.category == "internal_context":
            if "db" not in kwargs:
                if self.db is None:
                    raise ValueError(
                        f"Tool '{tool_name}' requires a database session in ToolRegistry."
                    )
                kwargs["db"] = self.db
        elif self.binance_client is not None and "client" not in kwargs:
            kwargs["client"] = self.binance_client

        result = tool.callable(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


def _default_tool_definitions() -> list[RegisteredTool]:
    return [
        RegisteredTool(
            name="crypto_market_rank",
            category="binance_skill",
            description="Fetch current Binance trending-token rank or smart-money inflow rank data.",
            input_schema={
                "chain_id": "string|null",
                "mode": "trending_tokens|smart_money_inflow_rank",
                "contract_address": "string|null",
                "symbol": "string|null",
                "size": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=crypto_market_rank,
        ),
        RegisteredTool(
            name="query_token_info",
            category="binance_skill",
            description="Fetch Binance token metadata plus dynamic market data for a token.",
            input_schema={
                "chain_id": "string",
                "contract_address": "string",
                "include_dynamic": "boolean",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=query_token_info,
        ),
        RegisteredTool(
            name="query_token_audit",
            category="binance_skill",
            description="Fetch Binance token audit information for a token contract.",
            input_schema={
                "chain_id": "string",
                "contract_address": "string",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=query_token_audit,
        ),
        RegisteredTool(
            name="trading_signal",
            category="binance_skill",
            description="Fetch Binance smart-money trading signals for a chain or token.",
            input_schema={
                "chain_id": "string",
                "contract_address": "string|null",
                "page_size": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=trading_signal,
        ),
        RegisteredTool(
            name="query_address_info",
            category="binance_skill",
            description="Fetch Binance address positions or address PnL ranking data.",
            input_schema={
                "chain_id": "string",
                "address": "string|null",
                "mode": "positions|pnl_rank",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=query_address_info,
        ),
        RegisteredTool(
            name="get_trending_token_context",
            category="internal_context",
            description="Read stored local token context including KOL, insight, and risk summaries for trending tokens.",
            input_schema={
                "chain_id": "string|null",
                "limit": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=get_trending_token_context,
        ),
        RegisteredTool(
            name="get_token_context",
            category="internal_context",
            description="Read stored local context for a specific token from the database.",
            input_schema={
                "chain_id": "string",
                "contract_address": "string",
                "limit": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=get_token_context,
        ),
        RegisteredTool(
            name="search_kol_mentions",
            category="internal_context",
            description="Search stored KOL posts and extracted token mentions from the local database.",
            input_schema={
                "query": "string|null",
                "chain_id": "string|null",
                "contract_address": "string|null",
                "handle": "string|null",
                "limit": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=search_kol_mentions,
        ),
        RegisteredTool(
            name="get_kol_summary",
            category="internal_context",
            description="Read stored KOL profile summaries or a detailed local summary for one KOL handle.",
            input_schema={
                "handle": "string|null",
                "limit": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=get_kol_summary,
        ),
        RegisteredTool(
            name="get_latest_insight",
            category="internal_context",
            description="Read the latest stored deterministic insight for a token from the database.",
            input_schema={
                "chain_id": "string",
                "contract_address": "string",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=get_latest_insight,
        ),
        RegisteredTool(
            name="get_high_risk_tokens",
            category="internal_context",
            description="Read and rank locally stored tokens by audit, liquidity, concentration, and safety risk signals.",
            input_schema={
                "chain_id": "string|null",
                "limit": "integer",
            },
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=get_high_risk_tokens,
        ),
        RegisteredTool(
            name="get_data_mode_status",
            category="internal_context",
            description="Read local backend data mode, enabled chains, record counts, and freshness timestamps.",
            input_schema={},
            output_schema=_TOOL_OUTPUT_SCHEMA,
            callable=get_data_mode_status,
        ),
    ]


__all__ = ["RegisteredTool", "ToolRegistry"]
