from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from app.clients import BinanceSkillsClient
from app.schemas import AgentToolResult
from app.services.market_ingestion import build_chain_option

TOOL_SOURCE = "binance_skills"
POSITIVE_DIRECTIONS = {"buy", "long", "accumulate", "bullish"}
NEGATIVE_DIRECTIONS = {"sell", "short", "bearish", "exit"}

CryptoMarketRankMode = Literal["trending_tokens", "smart_money_inflow_rank"]
QueryAddressInfoMode = Literal["positions", "pnl_rank"]


@asynccontextmanager
async def _borrow_client(
    client: BinanceSkillsClient | None,
):
    if client is not None:
        yield client
        return

    async with BinanceSkillsClient() as owned_client:
        yield owned_client


async def crypto_market_rank(
    *,
    chain_id: str | None = None,
    mode: CryptoMarketRankMode = "trending_tokens",
    period: int | str | None = None,
    page: int = 1,
    size: int = 100,
    sort_by: int = 0,
    order_asc: bool = False,
    tag_type: int = 2,
    contract_address: str | None = None,
    symbol: str | None = None,
    client: BinanceSkillsClient | None = None,
) -> AgentToolResult:
    input_args = {
        "chain_id": chain_id,
        "mode": mode,
        "period": period,
        "page": page,
        "size": size,
        "sort_by": sort_by,
        "order_asc": order_asc,
        "tag_type": tag_type,
        "contract_address": contract_address,
        "symbol": symbol,
    }
    started_at = time.perf_counter()

    try:
        async with _borrow_client(client) as skill_client:
            if mode == "smart_money_inflow_rank":
                if not chain_id:
                    raise ValueError("chain_id is required for smart_money_inflow_rank")
                result = await skill_client.get_smart_money_inflow_rank(
                    chain_id=chain_id,
                    period=str(period or "24h"),
                    tag_type=tag_type,
                )
                tool_name = "smart_money_inflow_rank"
            else:
                period_value = int(period) if isinstance(period, int) else 50
                result = await skill_client.get_trending_token_rank(
                    chain_id=chain_id,
                    period=period_value,
                    page=page,
                    size=size,
                    sort_by=sort_by,
                    order_asc=order_asc,
                )
                tool_name = "trending_token_rank"

        items = _extract_items(result.data)
        filtered_items = _filter_token_items(
            items,
            contract_address=contract_address,
            symbol=symbol,
        )
        working_items = filtered_items if contract_address or symbol else items
        payload = {
            "items": _jsonable(working_items),
            "match_count": len(working_items),
            "total_items": len(items),
            "matched": _jsonable(working_items[0]) if len(working_items) == 1 else None,
        }
        return _success_result(
            skill_name="crypto_market_rank",
            tool_name=tool_name,
            input_args=input_args,
            data=payload,
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            skill_name="crypto_market_rank",
            tool_name=mode,
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def query_token_info(
    *,
    chain_id: str,
    contract_address: str,
    include_dynamic: bool = True,
    client: BinanceSkillsClient | None = None,
) -> AgentToolResult:
    input_args = {
        "chain_id": chain_id,
        "contract_address": contract_address,
        "include_dynamic": include_dynamic,
    }
    started_at = time.perf_counter()

    try:
        async with _borrow_client(client) as skill_client:
            metadata_task = skill_client.get_token_metadata(chain_id, contract_address)
            dynamic_task = (
                skill_client.get_token_dynamic_market_data(chain_id, contract_address)
                if include_dynamic
                else None
            )

            if dynamic_task is None:
                metadata_result = await metadata_task
                dynamic_result: Any = None
            else:
                metadata_result, dynamic_result = await asyncio.gather(
                    metadata_task,
                    dynamic_task,
                    return_exceptions=True,
                )

        if isinstance(metadata_result, Exception):
            raise metadata_result

        status = "ok"
        error_message: str | None = None
        dynamic_payload: Any = None
        if isinstance(dynamic_result, Exception):
            status = "partial"
            error_message = str(dynamic_result)
        elif dynamic_result is not None:
            dynamic_payload = dynamic_result.data

        payload = {
            "metadata": _jsonable(metadata_result.data),
            "dynamic_market_data": _jsonable(dynamic_payload),
            "display_label": _metadata_display_label(metadata_result.data, chain_id=chain_id),
        }
        return _success_result(
            skill_name="query_token_info",
            tool_name="token_info_bundle" if include_dynamic else "token_metadata",
            input_args=input_args,
            data=payload,
            started_at=started_at,
            status=status,
            error=error_message,
        )
    except Exception as exc:
        return _error_result(
            skill_name="query_token_info",
            tool_name="token_info_bundle" if include_dynamic else "token_metadata",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def query_token_audit(
    *,
    chain_id: str,
    contract_address: str,
    client: BinanceSkillsClient | None = None,
) -> AgentToolResult:
    input_args = {
        "chain_id": chain_id,
        "contract_address": contract_address,
    }
    started_at = time.perf_counter()

    try:
        async with _borrow_client(client) as skill_client:
            result = await skill_client.get_token_audit(chain_id, contract_address)

        return _success_result(
            skill_name="query_token_audit",
            tool_name="token_audit",
            input_args=input_args,
            data=_jsonable(result.data),
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            skill_name="query_token_audit",
            tool_name="token_audit",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def trading_signal(
    *,
    chain_id: str,
    contract_address: str | None = None,
    page: int = 1,
    page_size: int = 100,
    smart_signal_type: str = "",
    client: BinanceSkillsClient | None = None,
) -> AgentToolResult:
    input_args = {
        "chain_id": chain_id,
        "contract_address": contract_address,
        "page": page,
        "page_size": page_size,
        "smart_signal_type": smart_signal_type,
    }
    started_at = time.perf_counter()

    try:
        async with _borrow_client(client) as skill_client:
            result = await skill_client.get_smart_money_signals(
                chain_id,
                page=page,
                page_size=page_size,
                smart_signal_type=smart_signal_type,
            )

        items = _extract_items(result.data)
        filtered_items = _filter_token_items(items, contract_address=contract_address, symbol=None)
        working_items = filtered_items if contract_address else items
        payload = {
            "items": _jsonable(working_items),
            "match_count": len(filtered_items),
            "signal_count": len(working_items),
            "positive_count": _count_signal_directions(working_items, POSITIVE_DIRECTIONS),
            "negative_count": _count_signal_directions(working_items, NEGATIVE_DIRECTIONS),
        }
        return _success_result(
            skill_name="trading_signal",
            tool_name="smart_money_signals",
            input_args=input_args,
            data=payload,
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            skill_name="trading_signal",
            tool_name="smart_money_signals",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def query_address_info(
    *,
    chain_id: str,
    address: str | None = None,
    mode: QueryAddressInfoMode = "positions",
    offset: int = 0,
    period: str = "30d",
    tag: str = "ALL",
    sort_by: int = 0,
    order_by: int = 0,
    page_no: int = 1,
    page_size: int = 25,
    filters: dict[str, Any] | None = None,
    client: BinanceSkillsClient | None = None,
) -> AgentToolResult:
    input_args = {
        "chain_id": chain_id,
        "address": address,
        "mode": mode,
        "offset": offset,
        "period": period,
        "tag": tag,
        "sort_by": sort_by,
        "order_by": order_by,
        "page_no": page_no,
        "page_size": page_size,
        "filters": filters,
    }
    started_at = time.perf_counter()

    try:
        async with _borrow_client(client) as skill_client:
            if mode == "pnl_rank":
                result = await skill_client.get_address_pnl_rank(
                    chain_id,
                    period=period,
                    tag=tag,
                    sort_by=sort_by,
                    order_by=order_by,
                    page_no=page_no,
                    page_size=page_size,
                    filters=filters,
                )
                tool_name = "address_pnl_rank"
            else:
                if not address:
                    raise ValueError("address is required for positions mode")
                result = await skill_client.get_address_positions(
                    address=address,
                    chain_id=chain_id,
                    offset=offset,
                )
                tool_name = "address_positions"

        return _success_result(
            skill_name="query_address_info",
            tool_name=tool_name,
            input_args=input_args,
            data=_jsonable(result.data),
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            skill_name="query_address_info",
            tool_name="address_pnl_rank" if mode == "pnl_rank" else "address_positions",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


def _success_result(
    *,
    skill_name: str,
    tool_name: str,
    input_args: dict[str, Any],
    data: Any,
    started_at: float,
    status: str = "ok",
    error: str | None = None,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=skill_name,
        tool_name=tool_name,
        input_args=_jsonable(input_args),
        source=TOOL_SOURCE,
        status=status,
        latency_ms=_latency_ms(started_at),
        fetched_at=_now(),
        data=_jsonable(data),
        error=error,
    )


def _error_result(
    *,
    skill_name: str,
    tool_name: str,
    input_args: dict[str, Any],
    error: str,
    started_at: float,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=skill_name,
        tool_name=tool_name,
        input_args=_jsonable(input_args),
        source=TOOL_SOURCE,
        status="error",
        latency_ms=_latency_ms(started_at),
        fetched_at=_now(),
        data=None,
        error=error,
    )


def _extract_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if isinstance(value, dict):
        for key in ("items", "list", "rows", "rank", "tokens", "signals", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]

    return []


def _filter_token_items(
    items: list[dict[str, Any]],
    *,
    contract_address: str | None,
    symbol: str | None,
) -> list[dict[str, Any]]:
    contract_match = contract_address.lower() if contract_address else None
    symbol_match = symbol.upper() if symbol else None
    filtered: list[dict[str, Any]] = []

    for item in items:
        item_contract = str(item.get("contractAddress") or item.get("ca") or "").lower()
        item_symbol = str(item.get("symbol") or item.get("ticker") or "").upper()

        if contract_match and item_contract == contract_match:
            filtered.append(item)
            continue

        if symbol_match and item_symbol == symbol_match:
            filtered.append(item)

    return filtered


def _count_signal_directions(
    items: list[dict[str, Any]],
    directions: set[str],
) -> int:
    count = 0
    for item in items:
        direction = str(item.get("direction") or "").strip().lower()
        if direction in directions:
            count += 1
    return count


def _metadata_display_label(metadata: Any, *, chain_id: str) -> str | None:
    if not isinstance(metadata, dict):
        return None

    symbol = str(metadata.get("symbol") or "").strip()
    name = str(metadata.get("name") or "").strip()
    contract_address = str(metadata.get("contractAddress") or "").strip()

    if name and symbol and name.casefold() != symbol.casefold():
        base_label = f"{name} ({symbol})"
    else:
        base_label = symbol or name or contract_address

    if not base_label:
        return None

    chain_short_name = build_chain_option(chain_id)["short_name"]
    return f"{base_label} on {chain_short_name}"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return _to_utc(value).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {str(key): _jsonable(sub_value) for key, sub_value in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


def _latency_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _now() -> datetime:
    return datetime.now(UTC)
