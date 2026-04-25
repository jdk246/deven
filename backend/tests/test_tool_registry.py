from __future__ import annotations

import asyncio

import pytest

from app.agent_tools.registry import ToolRegistry
from app.schemas import AgentToolResult


def test_registry_includes_all_required_tools(db_session) -> None:
    registry = ToolRegistry(db=db_session)
    tool_names = {tool["name"] for tool in registry.list_agent_tools()}

    expected = {
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
        "rank_kols_by_track_record",
        "get_kol_track_record",
        "get_kol_call_examples",
    }
    assert expected.issubset(tool_names)


def test_list_agent_tools_returns_api_friendly_metadata(db_session) -> None:
    registry = ToolRegistry(db=db_session)
    tools = registry.list_agent_tools()

    assert tools
    for tool in tools:
        assert set(tool) == {"name", "category", "description", "input_schema", "output_schema"}
        assert isinstance(tool["name"], str)
        assert isinstance(tool["category"], str)
        assert isinstance(tool["description"], str)
        assert isinstance(tool["input_schema"], dict)
        assert isinstance(tool["output_schema"], dict)


def test_call_tool_executes_a_registered_tool(db_session) -> None:
    registry = ToolRegistry(db=db_session)
    result = asyncio.run(registry.call_tool("get_data_mode_status", {}))

    assert isinstance(result, AgentToolResult)
    assert result.tool_name == "get_data_mode_status"
    assert result.status == "ok"


def test_unknown_tool_name_fails_cleanly(db_session) -> None:
    registry = ToolRegistry(db=db_session)

    with pytest.raises(ValueError, match="Unknown tool"):
        asyncio.run(registry.call_tool("does_not_exist", {}))


def test_tool_categories_are_correct(db_session) -> None:
    registry = ToolRegistry(db=db_session)
    tools = registry.list_agent_tools()

    binance_tools = [tool for tool in tools if tool["category"] == "binance_skill"]
    internal_tools = [tool for tool in tools if tool["category"] == "internal_context"]

    assert len(binance_tools) == 5
    assert len(internal_tools) == 10
