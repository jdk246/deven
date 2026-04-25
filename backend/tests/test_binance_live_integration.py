from __future__ import annotations

import asyncio
import os

import pytest

from app.agent_tools.binance_skill_tools import crypto_market_rank, query_token_audit, query_token_info
from app.schemas import AgentToolResult

pytestmark = pytest.mark.integration


def _assert_agent_tool_result(result: AgentToolResult) -> None:
    assert isinstance(result, AgentToolResult)
    assert result.skill_name
    assert result.tool_name
    assert isinstance(result.input_args, dict)
    assert result.source
    assert result.status
    assert isinstance(result.latency_ms, int)
    assert result.fetched_at is not None


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "").lower() != "true",
    reason="Set RUN_INTEGRATION_TESTS=true to run live Binance integration tests.",
)
def test_live_binance_tool_flow_is_graceful() -> None:
    rank_result = asyncio.run(crypto_market_rank(chain_id="56", mode="trending_tokens", size=5))
    _assert_agent_tool_result(rank_result)
    assert rank_result.status in {"ok", "partial", "error"}

    if rank_result.status not in {"ok", "partial"}:
        return

    items = []
    if isinstance(rank_result.data, dict):
        raw_items = rank_result.data.get("items")
        if isinstance(raw_items, list):
            items = [item for item in raw_items if isinstance(item, dict)]

    token_row = next(
        (
            item
            for item in items
            if item.get("contractAddress") or item.get("contract_address") or item.get("ca")
        ),
        None,
    )
    if token_row is None:
        return

    contract_address = (
        token_row.get("contractAddress")
        or token_row.get("contract_address")
        or token_row.get("ca")
    )
    chain_id = str(token_row.get("chainId") or token_row.get("chain_id") or "56")

    info_result = asyncio.run(
        query_token_info(chain_id=chain_id, contract_address=str(contract_address))
    )
    audit_result = asyncio.run(
        query_token_audit(chain_id=chain_id, contract_address=str(contract_address))
    )

    _assert_agent_tool_result(info_result)
    _assert_agent_tool_result(audit_result)
    assert info_result.status in {"ok", "partial", "error"}
    assert audit_result.status in {"ok", "partial", "error"}
