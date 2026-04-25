from __future__ import annotations

import asyncio

from app.agent_tools.binance_skill_tools import (
    crypto_market_rank,
    query_address_info,
    query_token_audit,
    query_token_info,
    trading_signal,
)
from app.agent_tools.registry import ToolRegistry
from app.agent_tools.database_context_tools import (
    get_data_mode_status,
    get_high_risk_tokens,
    get_kol_summary,
    get_latest_insight,
    get_token_context,
    get_trending_token_context,
    search_kol_mentions,
)
from app.clients.binance_skills import BinanceSkillsResult
from app.schemas import AgentToolResult


class FakeBinanceClient:
    async def get_trending_token_rank(self, **_: object) -> BinanceSkillsResult:
        rows = [{"chainId": "56", "contractAddress": "0x1", "symbol": "BNB"}]
        return BinanceSkillsResult(data=rows, raw={"data": rows})

    async def get_token_metadata(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        payload = {"chainId": chain_id, "contractAddress": contract_address, "symbol": "BNB", "name": "BNB"}
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_token_dynamic_market_data(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        payload = {
            "chainId": chain_id,
            "contractAddress": contract_address,
            "price": 650.0,
            "percentChange24h": 4.2,
            "volume24h": 1_500_000.0,
            "liquidity": 850_000.0,
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_token_audit(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        payload = {
            "chainId": chain_id,
            "contractAddress": contract_address,
            "hasResult": True,
            "riskLevelEnum": "LOW",
            "extraInfo": {"isVerified": True, "buyTax": 0.0, "sellTax": 0.0},
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_smart_money_signals(self, chain_id: str, **_: object) -> BinanceSkillsResult:
        rows = [
            {
                "chainId": chain_id,
                "contractAddress": "0x1",
                "direction": "buy",
                "ticker": "BNB",
            }
        ]
        return BinanceSkillsResult(data=rows, raw={"data": rows})

    async def get_address_positions(self, address: str, chain_id: str, **_: object) -> BinanceSkillsResult:
        payload = {"chainId": chain_id, "address": address, "items": [{"symbol": "BNB"}]}
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_address_pnl_rank(self, chain_id: str, **_: object) -> BinanceSkillsResult:
        payload = {"chainId": chain_id, "rows": [{"address": "0xabc", "pnl": 12.5}]}
        return BinanceSkillsResult(data=payload, raw={"data": payload})


class BrokenBinanceClient:
    async def get_trending_token_rank(self, **_: object) -> BinanceSkillsResult:
        raise RuntimeError("boom")


def _assert_agent_tool_shape(result: AgentToolResult) -> None:
    assert isinstance(result, AgentToolResult)
    assert result.skill_name
    assert result.tool_name
    assert isinstance(result.input_args, dict)
    assert result.source
    assert result.status
    assert isinstance(result.latency_ms, int)
    assert result.fetched_at is not None


def test_tool_registry_lists_all_required_tools(db_session) -> None:
    registry = ToolRegistry(db=db_session)
    tool_names = {tool["name"] for tool in registry.list_agent_tools()}

    assert {
        "crypto_market_rank",
        "query_token_info",
        "query_token_audit",
        "trading_signal",
        "query_address_info",
        "get_trending_token_context",
        "get_token_context",
        "search_kol_mentions",
        "get_kol_summary",
        "get_latest_insight",
        "get_high_risk_tokens",
        "get_data_mode_status",
    }.issubset(tool_names)


def test_crypto_market_rank_returns_agent_tool_result() -> None:
    result = asyncio.run(crypto_market_rank(chain_id="56", client=FakeBinanceClient()))

    _assert_agent_tool_shape(result)
    assert result.skill_name == "crypto_market_rank"
    assert result.source == "binance_skills"
    assert result.data["match_count"] == 1


def test_query_token_info_returns_agent_tool_result() -> None:
    result = asyncio.run(
        query_token_info(
            chain_id="56",
            contract_address="0x1",
            client=FakeBinanceClient(),
        )
    )

    _assert_agent_tool_shape(result)
    assert result.skill_name == "query_token_info"
    assert result.data["metadata"]["symbol"] == "BNB"
    assert result.data["dynamic_market_data"]["price"] == 650.0


def test_query_token_audit_returns_agent_tool_result() -> None:
    result = asyncio.run(
        query_token_audit(
            chain_id="56",
            contract_address="0x1",
            client=FakeBinanceClient(),
        )
    )

    _assert_agent_tool_shape(result)
    assert result.skill_name == "query_token_audit"
    assert result.data["riskLevelEnum"] == "LOW"


def test_trading_signal_returns_agent_tool_result() -> None:
    result = asyncio.run(
        trading_signal(
            chain_id="56",
            contract_address="0x1",
            client=FakeBinanceClient(),
        )
    )

    _assert_agent_tool_shape(result)
    assert result.skill_name == "trading_signal"
    assert result.data["signal_count"] == 1
    assert result.data["positive_count"] == 1


def test_query_address_info_returns_agent_tool_result_for_positions_and_pnl() -> None:
    positions_result = asyncio.run(
        query_address_info(
            chain_id="56",
            address="0xabc",
            mode="positions",
            client=FakeBinanceClient(),
        )
    )
    pnl_result = asyncio.run(
        query_address_info(
            chain_id="56",
            mode="pnl_rank",
            client=FakeBinanceClient(),
        )
    )

    _assert_agent_tool_shape(positions_result)
    _assert_agent_tool_shape(pnl_result)
    assert positions_result.skill_name == "query_address_info"
    assert pnl_result.skill_name == "query_address_info"


def test_tool_failures_return_error_status() -> None:
    result = asyncio.run(crypto_market_rank(chain_id="56", client=BrokenBinanceClient()))

    _assert_agent_tool_shape(result)
    assert result.status == "error"
    assert result.error


def test_internal_database_context_tools_return_empty_status_in_empty_db(db_session) -> None:
    async def runner():
        return [
            await get_trending_token_context(db=db_session),
            await get_token_context(db=db_session, chain_id="56", contract_address="0x1"),
            await search_kol_mentions(db=db_session, query="BNB"),
            await get_kol_summary(db=db_session, handle="missing"),
            await get_latest_insight(db=db_session, chain_id="56", contract_address="0x1"),
            await get_high_risk_tokens(db=db_session),
            await get_data_mode_status(db=db_session),
        ]

    results = asyncio.run(runner())

    for result in results[:-1]:
        _assert_agent_tool_shape(result)
        assert result.status == "empty"

    _assert_agent_tool_shape(results[-1])
    assert results[-1].status == "ok"
