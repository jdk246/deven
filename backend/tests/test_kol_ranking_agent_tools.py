from __future__ import annotations

import asyncio

from app.agent_tools.database_context_tools import (
    get_kol_call_examples,
    get_kol_track_record,
    rank_kols_by_track_record,
)
from app.agent_tools.registry import ToolRegistry
from app.schemas import AgentToolResult
from app.services.kol_performance import KOLPerformanceService
from tests.helpers import seed_kol_performance_history


def test_kol_ranking_tools_return_agent_tool_result(db_session) -> None:
    seed_kol_performance_history(db_session)
    KOLPerformanceService(db_session).refresh_kol_performance()

    async def runner():
        return [
            await rank_kols_by_track_record(db=db_session, limit=5),
            await get_kol_track_record(db=db_session, handle="alpha_calls"),
            await get_kol_call_examples(db=db_session, handle="alpha_calls", limit=3),
        ]

    results = asyncio.run(runner())

    assert all(isinstance(result, AgentToolResult) for result in results)
    assert all(result.status == "ok" for result in results)


def test_kol_ranking_tools_are_registered(db_session) -> None:
    tool_names = {tool["name"] for tool in ToolRegistry(db=db_session).list_agent_tools()}
    assert {
        "rank_kols_by_track_record",
        "get_kol_track_record",
        "get_kol_call_examples",
    }.issubset(tool_names)


def test_empty_db_returns_empty_not_error(db_session) -> None:
    async def runner():
        return [
            await rank_kols_by_track_record(db=db_session),
            await get_kol_track_record(db=db_session, handle="missing"),
            await get_kol_call_examples(db=db_session),
        ]

    results = asyncio.run(runner())
    assert all(result.status == "empty" for result in results)
