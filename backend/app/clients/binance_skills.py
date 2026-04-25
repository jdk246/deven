"""Backend-only client for Binance Skills APIs.

This module is intentionally kept behind the backend boundary. Frontend code
should consume backend routes and never call Binance endpoints directly.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

import httpx

from app.config import get_settings

JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None

TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_HEADERS = {"Accept-Encoding": "identity"}
STRING_ID_KEYS = {
    "address",
    "binanceChainId",
    "ca",
    "chainId",
    "contractAddress",
    "requestId",
    "signalId",
    "symbol",
    "ticker",
    "tokenId",
}
INT_KEY_PATTERNS = (
    re.compile(r".*Time$"),
    re.compile(r".*Count$"),
    re.compile(r".*Cnt$"),
    re.compile(r"^count([0-9]+[mhdw])?(Buy|Sell)?$"),
    re.compile(r"^page(No|Size)?$"),
    re.compile(r"^pages$"),
    re.compile(r"^current$"),
    re.compile(r"^size$"),
    re.compile(r"^total$"),
    re.compile(r"^rank(Type)?$"),
    re.compile(r"^sortBy$"),
    re.compile(r"^orderBy$"),
    re.compile(r"^orderAsc$"),
    re.compile(r"^period$"),
    re.compile(r"^(decimals|tokenDecimals|riskLevel|traders|priority)$"),
)
DECIMAL_KEY_PATTERNS = (
    re.compile(r".*Price.*", re.IGNORECASE),
    re.compile(r".*Volume.*", re.IGNORECASE),
    re.compile(r".*Cap.*", re.IGNORECASE),
    re.compile(r".*Liquidity.*", re.IGNORECASE),
    re.compile(r".*Percent.*", re.IGNORECASE),
    re.compile(r".*Pnl.*", re.IGNORECASE),
    re.compile(r".*Profit.*", re.IGNORECASE),
    re.compile(r".*Tax.*", re.IGNORECASE),
    re.compile(r".*Supply.*", re.IGNORECASE),
    re.compile(r".*Qty.*", re.IGNORECASE),
    re.compile(r".*Value.*", re.IGNORECASE),
    re.compile(r".*Rate.*", re.IGNORECASE),
    re.compile(r".*Score.*", re.IGNORECASE),
    re.compile(r".*Holding.*", re.IGNORECASE),
    re.compile(r"^balance$", re.IGNORECASE),
    re.compile(r"^inflow$", re.IGNORECASE),
    re.compile(r"^holders$", re.IGNORECASE),
    re.compile(r"^kycHolders$", re.IGNORECASE),
    re.compile(r"^kolHolders$", re.IGNORECASE),
    re.compile(r"^smartMoneyHolders$", re.IGNORECASE),
    re.compile(r"^proHolders$", re.IGNORECASE),
)
ICON_KEY_PATTERNS = (
    re.compile(r".*icon.*", re.IGNORECASE),
    re.compile(r".*logo.*", re.IGNORECASE),
)


class BinanceSkillsError(RuntimeError):
    """Raised when Binance Skills returns an unusable response."""


@dataclass(slots=True)
class BinanceSkillsResult:
    """Normalized payload alongside the untouched raw Binance response."""

    data: JSONValue
    raw: dict[str, Any]


class BinanceSkillsClient:
    """Async backend client for Binance Skills endpoints."""

    TOKEN_INFO_USER_AGENT = "binance-web3/1.1 (Skill)"
    TRADING_SIGNAL_USER_AGENT = "binance-web3/1.1 (Skill)"
    ADDRESS_INFO_USER_AGENT = "binance-web3/1.1 (Skill)"
    TOKEN_AUDIT_USER_AGENT = "binance-web3/1.4 (Skill)"
    MARKET_RANK_USER_AGENT = "binance-web3/2.1 (Skill)"

    TRENDING_TOKEN_RANK_PATH = (
        "/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list/ai"
    )
    TOKEN_METADATA_PATH = (
        "/bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info/ai"
    )
    TOKEN_DYNAMIC_DATA_PATH = (
        "/bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info/ai"
    )
    TOKEN_AUDIT_PATH = "/bapi/defi/v1/public/wallet-direct/security/token/audit"
    SMART_MONEY_SIGNALS_PATH = (
        "/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money/ai"
    )
    SMART_MONEY_INFLOW_RANK_PATH = (
        "/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query/ai"
    )
    ADDRESS_PNL_RANK_PATH = "/bapi/defi/v1/public/wallet-direct/market/leaderboard/query/ai"
    ADDRESS_POSITIONS_PATH = (
        "/bapi/defi/v3/public/wallet-direct/buw/wallet/address/pnl/active-position-list/ai"
    )

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()

        self._base_url = (base_url or settings.binance_skills_base_url).rstrip("/")
        self._icon_base_url = settings.binance_icon_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds or settings.binance_request_timeout_seconds
        self._max_retries = max(0, max_retries if max_retries is not None else settings.binance_max_retries)
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> BinanceSkillsClient:
        await self._ensure_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def get_trending_token_rank(
        self,
        *,
        chain_id: str | None = None,
        period: int = 50,
        page: int = 1,
        size: int = 100,
        sort_by: int = 0,
        order_asc: bool = False,
    ) -> BinanceSkillsResult:
        payload: dict[str, Any] = {
            "rankType": 10,
            "period": period,
            "sortBy": sort_by,
            "orderAsc": order_asc,
            "page": page,
            "size": size,
        }
        if chain_id:
            payload["chainId"] = chain_id

        raw = await self._request_json(
            "POST",
            self.TRENDING_TOKEN_RANK_PATH,
            json_body=payload,
            headers=self._headers(self.MARKET_RANK_USER_AGENT, json_request=True),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=dict),
            raw=raw,
        )

    async def get_trending_tokens(self, **kwargs: Any) -> BinanceSkillsResult:
        return await self.get_trending_token_rank(**kwargs)

    async def get_token_metadata(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        raw = await self._request_json(
            "GET",
            self.TOKEN_METADATA_PATH,
            params={"chainId": chain_id, "contractAddress": contract_address},
            headers=self._headers(self.TOKEN_INFO_USER_AGENT),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=dict),
            raw=raw,
        )

    async def get_token_dynamic_market_data(
        self,
        chain_id: str,
        contract_address: str,
    ) -> BinanceSkillsResult:
        raw = await self._request_json(
            "GET",
            self.TOKEN_DYNAMIC_DATA_PATH,
            params={"chainId": chain_id, "contractAddress": contract_address},
            headers=self._headers(self.TOKEN_INFO_USER_AGENT),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=dict),
            raw=raw,
        )

    async def get_token_dynamic_data(
        self,
        chain_id: str,
        contract_address: str,
    ) -> BinanceSkillsResult:
        return await self.get_token_dynamic_market_data(chain_id, contract_address)

    async def get_token_audit(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        raw = await self._request_json(
            "POST",
            self.TOKEN_AUDIT_PATH,
            json_body={
                "binanceChainId": chain_id,
                "contractAddress": contract_address,
                "requestId": str(uuid4()),
            },
            headers=self._headers(
                self.TOKEN_AUDIT_USER_AGENT,
                extra_headers={"source": "agent"},
                json_request=True,
            ),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=dict),
            raw=raw,
        )

    async def get_smart_money_signals(
        self,
        chain_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        smart_signal_type: str = "",
    ) -> BinanceSkillsResult:
        raw = await self._request_json(
            "POST",
            self.SMART_MONEY_SIGNALS_PATH,
            json_body={
                "smartSignalType": smart_signal_type,
                "page": page,
                "pageSize": page_size,
                "chainId": chain_id,
            },
            headers=self._headers(self.TRADING_SIGNAL_USER_AGENT, json_request=True),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=list),
            raw=raw,
        )

    async def get_smart_money_inflow_rank(
        self,
        chain_id: str,
        *,
        period: str = "24h",
        tag_type: int = 2,
    ) -> BinanceSkillsResult:
        raw = await self._request_json(
            "POST",
            self.SMART_MONEY_INFLOW_RANK_PATH,
            json_body={
                "chainId": chain_id,
                "period": period,
                "tagType": tag_type,
            },
            headers=self._headers(self.MARKET_RANK_USER_AGENT, json_request=True),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=list),
            raw=raw,
        )

    async def get_address_pnl_rank(
        self,
        chain_id: str,
        *,
        period: str = "30d",
        tag: str = "ALL",
        sort_by: int = 0,
        order_by: int = 0,
        page_no: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
    ) -> BinanceSkillsResult:
        params: dict[str, Any] = {
            "chainId": chain_id,
            "period": period,
            "tag": tag,
            "sortBy": sort_by,
            "orderBy": order_by,
            "pageNo": page_no,
            "pageSize": page_size,
        }
        if filters:
            params.update(filters)

        raw = await self._request_json(
            "GET",
            self.ADDRESS_PNL_RANK_PATH,
            params=params,
            headers=self._headers(self.MARKET_RANK_USER_AGENT),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=dict),
            raw=raw,
        )

    async def get_address_positions(
        self,
        address: str,
        chain_id: str,
        *,
        offset: int = 0,
    ) -> BinanceSkillsResult:
        raw = await self._request_json(
            "GET",
            self.ADDRESS_POSITIONS_PATH,
            params={"address": address, "chainId": chain_id, "offset": offset},
            headers=self._headers(
                self.ADDRESS_INFO_USER_AGENT,
                extra_headers={"clienttype": "web", "clientversion": "1.2.0"},
            ),
        )
        return BinanceSkillsResult(
            data=self._unwrap_data(raw, default_factory=dict),
            raw=raw,
        )

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=DEFAULT_HEADERS.copy(),
                timeout=httpx.Timeout(self._timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    def _headers(
        self,
        user_agent: str,
        *,
        json_request: bool = False,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers = DEFAULT_HEADERS.copy()
        headers["User-Agent"] = user_agent
        if json_request:
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        response: httpx.Response | None = None
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json_body,
                    headers=headers,
                )

                if response.status_code in TRANSIENT_STATUS_CODES and attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue

                response.raise_for_status()
                payload = self._safe_json(response)

                if payload.get("success") is False:
                    message = payload.get("message") or payload.get("messageDetail") or "Binance request failed"
                    raise BinanceSkillsError(f"{message} (code={payload.get('code', 'unknown')})")

                return payload
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
                raise BinanceSkillsError(f"Binance request failed for {path}: {exc}") from exc
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in TRANSIENT_STATUS_CODES and attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
                raise BinanceSkillsError(self._http_error_message(path, exc.response)) from exc
            except BinanceSkillsError as exc:
                last_error = exc
                raise

        raise BinanceSkillsError(f"Binance request failed for {path}: {last_error}")

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep(0.5 * (2**attempt))

    def _safe_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise BinanceSkillsError(
                f"Invalid JSON returned from Binance endpoint {response.request.url}"
            ) from exc

        if not isinstance(payload, dict):
            raise BinanceSkillsError(
                f"Unexpected Binance payload type {type(payload).__name__} from {response.request.url}"
            )

        return payload

    def _http_error_message(self, path: str, response: httpx.Response) -> str:
        body_preview = response.text[:300].strip()
        if body_preview:
            return f"Binance request failed for {path} with {response.status_code}: {body_preview}"
        return f"Binance request failed for {path} with {response.status_code}"

    def _unwrap_data(
        self,
        payload: dict[str, Any],
        *,
        default_factory: type[dict[str, Any]] | type[list[Any]],
    ) -> JSONValue:
        data = payload.get("data")
        if data is None:
            return default_factory()
        return self._normalize_value(data)

    def _normalize_value(self, value: JSONValue, *, key: str | None = None) -> JSONValue:
        if isinstance(value, dict):
            return {sub_key: self._normalize_value(sub_value, key=sub_key) for sub_key, sub_value in value.items()}

        if isinstance(value, list):
            return [self._normalize_value(item, key=key) for item in value]

        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if stripped == "":
            return value

        if key and key in STRING_ID_KEYS:
            return value

        if key and self._looks_like_icon_field(key) and stripped.startswith("/"):
            return f"{self._icon_base_url}{stripped}"

        if key and self._looks_like_int_field(key):
            parsed_int = self._safe_int(stripped)
            if parsed_int is not None:
                return parsed_int

        if key and self._looks_like_decimal_field(key):
            parsed_decimal = self._safe_decimal(stripped)
            if parsed_decimal is not None:
                return parsed_decimal

        return value

    def _looks_like_int_field(self, key: str) -> bool:
        return any(pattern.fullmatch(key) for pattern in INT_KEY_PATTERNS)

    def _looks_like_decimal_field(self, key: str) -> bool:
        return any(pattern.fullmatch(key) for pattern in DECIMAL_KEY_PATTERNS)

    def _looks_like_icon_field(self, key: str) -> bool:
        return any(pattern.fullmatch(key) for pattern in ICON_KEY_PATTERNS)

    def _safe_int(self, value: str) -> int | None:
        if re.fullmatch(r"-?\d+", value) is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _safe_decimal(self, value: str) -> Decimal | None:
        if re.fullmatch(r"-?\d+(\.\d+)?", value) is None:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None
