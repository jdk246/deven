from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.schemas import AgentToolResult


def make_agent_tool_result(
    *,
    skill_name: str,
    tool_name: str,
    source: str,
    data: Any = None,
    status: str = "ok",
    input_args: dict[str, Any] | None = None,
    error: str | None = None,
    latency_ms: int = 7,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=skill_name,
        tool_name=tool_name,
        input_args=input_args or {},
        source=source,
        status=status,
        latency_ms=latency_ms,
        fetched_at=datetime.now(UTC),
        data=data,
        error=error,
    )
