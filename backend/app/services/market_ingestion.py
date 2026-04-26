from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.clients import BinanceSkillsClient
from app.config import get_settings
from app.models import SmartMoneySignal, Token, TokenAudit, TokenSnapshot

SUPPORTED_CHAINS = {
    "56": {
        "name": "BNB Chain",
        "short_name": "BSC",
        "platform": "bsc",
        "enabled_by_default": True,
    },
    "CT_501": {
        "name": "Solana",
        "short_name": "SOL",
        "platform": "solana",
        "enabled_by_default": True,
    },
    "8453": {
        "name": "Base",
        "short_name": "BASE",
        "platform": "base",
        "enabled_by_default": False,
    },
}

DEFAULT_JOBS = ("market", "audits", "smart_money")

# Keep the demo grounded in Binance Skills-supported contracts rather than
# inventing a separate market source. These are the chain-specific
# representations we want to include alongside the trending feed.
CURATED_MAJOR_TOKEN_WATCHLIST = {
    "56": [
        {
            "contract_address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
            "symbol_override": "BNB",
            "name_override": "BNB",
        },
        {
            "contract_address": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
            "symbol_override": "ETH",
            "name_override": "Ethereum",
        },
        {
            "contract_address": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
            "symbol_override": "BTC",
            "name_override": "Bitcoin",
        },
    ],
    "CT_501": [
        {
            "contract_address": "So11111111111111111111111111111111111111112",
            "symbol_override": "SOL",
            "name_override": "Solana",
        },
    ],
    "8453": [
        {
            "contract_address": "0x4200000000000000000000000000000000000006",
            "symbol_override": "ETH",
            "name_override": "Ethereum",
        },
    ],
}


def get_enabled_chain_ids() -> list[str]:
    settings = get_settings()
    requested = settings.enabled_chains or []
    chain_ids = [chain_id for chain_id in requested if chain_id in SUPPORTED_CHAINS]
    if chain_ids:
        return list(dict.fromkeys(chain_ids))

    return [
        chain_id
        for chain_id, chain in SUPPORTED_CHAINS.items()
        if bool(chain["enabled_by_default"])
    ]


def build_chain_option(chain_id: str) -> dict[str, Any]:
    info = SUPPORTED_CHAINS.get(
        chain_id,
        {
            "name": chain_id,
            "short_name": chain_id,
            "platform": "unknown",
            "enabled_by_default": False,
        },
    )
    enabled = chain_id in get_enabled_chain_ids()
    return {
        "chain_id": chain_id,
        "name": str(info["name"]),
        "short_name": str(info["short_name"]),
        "platform": str(info["platform"]),
        "enabled_by_default": bool(info["enabled_by_default"]),
        "enabled": enabled,
    }


def get_curated_watchlist(chain_id: str) -> list[dict[str, str]]:
    return [dict(item) for item in CURATED_MAJOR_TOKEN_WATCHLIST.get(chain_id, [])]


class MarketIngestionService:
    def __init__(
        self,
        db: Session,
        binance_client: BinanceSkillsClient,
    ) -> None:
        self.db = db
        self.binance_client = binance_client

    async def run_refresh(
        self,
        *,
        jobs: Sequence[str] | None = None,
        chains: Sequence[str] | None = None,
        limit_per_chain: int = 20,
    ) -> dict[str, Any]:
        selected_jobs, ignored_jobs = self._resolve_jobs(jobs)
        selected_chains, ignored_chains = self._resolve_chains(chains)
        clamped_limit = max(1, min(limit_per_chain, 100))

        response: dict[str, Any] = {
            "status": "ok",
            "jobs": selected_jobs,
            "chains": [build_chain_option(chain_id) for chain_id in selected_chains],
            "limit_per_chain": clamped_limit,
            "summary": [],
            "errors": [],
        }

        if ignored_jobs:
            response["errors"].append(f"Ignored unsupported jobs: {', '.join(ignored_jobs)}")
        if ignored_chains:
            response["errors"].append(f"Ignored unsupported chains: {', '.join(ignored_chains)}")

        for chain_id in selected_chains:
            chain_summary = {
                "chain_id": chain_id,
                "chain_name": build_chain_option(chain_id)["name"],
                "tokens_seen": 0,
                "tokens_upserted": 0,
                "snapshots_created": 0,
                "audits_created": 0,
                "signals_upserted": 0,
                "watchlist_targets": len(get_curated_watchlist(chain_id)),
                "watchlist_upserted": 0,
                "errors": [],
            }
            processed_tokens: set[tuple[str, str]] = set()

            if "market" in selected_jobs or "audits" in selected_jobs:
                await self._ingest_trending_chain(
                    chain_id=chain_id,
                    limit_per_chain=clamped_limit,
                    jobs=selected_jobs,
                    summary=chain_summary,
                    processed_tokens=processed_tokens,
                )
                await self._ingest_curated_watchlist_chain(
                    chain_id=chain_id,
                    jobs=selected_jobs,
                    summary=chain_summary,
                    processed_tokens=processed_tokens,
                )

            if "smart_money" in selected_jobs:
                await self._ingest_smart_money_chain(
                    chain_id=chain_id,
                    limit_per_chain=clamped_limit,
                    summary=chain_summary,
                )

            response["summary"].append(chain_summary)

        return response

    async def _ingest_trending_chain(
        self,
        *,
        chain_id: str,
        limit_per_chain: int,
        jobs: Sequence[str],
        summary: dict[str, Any],
        processed_tokens: set[tuple[str, str]],
    ) -> None:
        try:
            trending_result = await self.binance_client.get_trending_token_rank(
                chain_id=chain_id,
                size=limit_per_chain,
            )
        except Exception as exc:
            summary["errors"].append(f"Trending token fetch failed: {exc}")
            return

        trending_tokens = self._extract_trending_tokens(trending_result.data, limit_per_chain)
        summary["tokens_seen"] = len(trending_tokens)

        for token_row in trending_tokens:
            contract_address = self._string_value(token_row.get("contractAddress") or token_row.get("ca"))
            effective_chain_id = self._string_value(token_row.get("chainId")) or chain_id

            if not contract_address:
                summary["errors"].append("Skipping token with missing contract address.")
                continue

            await self._ingest_token_contract(
                chain_id=effective_chain_id,
                contract_address=contract_address,
                jobs=jobs,
                summary=summary,
                processed_tokens=processed_tokens,
                source_rows=[token_row],
                source_label="trending token",
            )

    async def _ingest_curated_watchlist_chain(
        self,
        *,
        chain_id: str,
        jobs: Sequence[str],
        summary: dict[str, Any],
        processed_tokens: set[tuple[str, str]],
    ) -> None:
        for watch_item in get_curated_watchlist(chain_id):
            contract_address = self._string_value(watch_item.get("contract_address"))
            if not contract_address:
                continue
            token_key = (chain_id, contract_address.lower())
            override_rows = [
                {
                    "symbol": watch_item.get("symbol_override"),
                    "name": watch_item.get("name_override"),
                }
            ]

            if token_key in processed_tokens:
                self._upsert_token(
                    chain_id=chain_id,
                    contract_address=contract_address,
                    source_rows=override_rows,
                )
                self._commit_or_recover(summary)
                summary["watchlist_upserted"] += 1
                continue

            ingested = await self._ingest_token_contract(
                chain_id=chain_id,
                contract_address=contract_address,
                jobs=jobs,
                summary=summary,
                processed_tokens=processed_tokens,
                source_rows=override_rows,
                source_label=f"watchlist token {watch_item.get('symbol_override') or contract_address}",
            )
            if ingested:
                summary["watchlist_upserted"] += 1

    async def _ingest_token_contract(
        self,
        *,
        chain_id: str,
        contract_address: str,
        jobs: Sequence[str],
        summary: dict[str, Any],
        processed_tokens: set[tuple[str, str]],
        source_rows: Sequence[dict[str, Any]],
        source_label: str,
    ) -> bool:
        token_key = (chain_id, contract_address.lower())
        if token_key in processed_tokens:
            return False

        metadata_payload: dict[str, Any] = {}

        if "market" in jobs:
            try:
                metadata_result = await self.binance_client.get_token_metadata(
                    chain_id,
                    contract_address,
                )
                metadata_payload = self._dict_data(metadata_result.data)
            except Exception as exc:
                summary["errors"].append(
                    f"Metadata fetch failed for {source_label} {chain_id}:{contract_address}: {exc}"
                )

        self._upsert_token(
            chain_id=chain_id,
            contract_address=contract_address,
            source_rows=[metadata_payload, *source_rows],
        )
        summary["tokens_upserted"] += 1

        if "market" in jobs:
            try:
                dynamic_result = await self.binance_client.get_token_dynamic_data(
                    chain_id,
                    contract_address,
                )
                dynamic_payload = self._dict_data(dynamic_result.data)
                self._store_snapshot(
                    chain_id=chain_id,
                    contract_address=contract_address,
                    dynamic_data=dynamic_payload,
                    raw_payload=dynamic_result.raw.get("data"),
                )
                summary["snapshots_created"] += 1
            except Exception as exc:
                summary["errors"].append(
                    f"Dynamic market fetch failed for {source_label} {chain_id}:{contract_address}: {exc}"
                )

        if "audits" in jobs:
            try:
                audit_result = await self.binance_client.get_token_audit(
                    chain_id,
                    contract_address,
                )
                audit_payload = self._dict_data(audit_result.data)
                if audit_payload:
                    self._store_audit(
                        chain_id=chain_id,
                        contract_address=contract_address,
                        audit_data=audit_payload,
                        raw_payload=audit_result.raw.get("data"),
                    )
                    summary["audits_created"] += 1
            except Exception as exc:
                summary["errors"].append(
                    f"Audit fetch failed for {source_label} {chain_id}:{contract_address}: {exc}"
                )

        self._commit_or_recover(summary)
        processed_tokens.add(token_key)
        return True

    async def _ingest_smart_money_chain(
        self,
        *,
        chain_id: str,
        limit_per_chain: int,
        summary: dict[str, Any],
    ) -> None:
        try:
            signal_result = await self.binance_client.get_smart_money_signals(
                chain_id,
                page_size=limit_per_chain,
            )
        except Exception as exc:
            summary["errors"].append(f"Smart-money fetch failed: {exc}")
            return

        signal_rows = self._list_data(signal_result.data)[:limit_per_chain]

        for signal_row in signal_rows:
            effective_chain_id = self._string_value(signal_row.get("chainId")) or chain_id
            contract_address = self._string_value(signal_row.get("contractAddress"))

            if not contract_address:
                summary["errors"].append("Skipping smart-money signal with missing contract address.")
                continue

            self._upsert_token(
                chain_id=effective_chain_id,
                contract_address=contract_address,
                source_rows=[signal_row],
            )
            self._upsert_signal(
                chain_id=effective_chain_id,
                contract_address=contract_address,
                signal_data=signal_row,
            )
            summary["signals_upserted"] += 1
            self._commit_or_recover(summary)

    def _resolve_jobs(self, jobs: Sequence[str] | None) -> tuple[list[str], list[str]]:
        requested_jobs = list(jobs or DEFAULT_JOBS)
        selected = [job for job in requested_jobs if job in DEFAULT_JOBS]
        ignored = [job for job in requested_jobs if job not in DEFAULT_JOBS]
        return list(dict.fromkeys(selected or list(DEFAULT_JOBS))), list(dict.fromkeys(ignored))

    def _resolve_chains(self, chains: Sequence[str] | None) -> tuple[list[str], list[str]]:
        requested = list(chains or get_enabled_chain_ids())
        selected = [chain_id for chain_id in requested if chain_id in SUPPORTED_CHAINS]
        ignored = [chain_id for chain_id in requested if chain_id not in SUPPORTED_CHAINS]
        if not selected:
            selected = get_enabled_chain_ids()
        return list(dict.fromkeys(selected)), list(dict.fromkeys(ignored))

    def _extract_trending_tokens(self, data: Any, limit: int) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [self._dict_data(row) for row in data[:limit]]

        payload = self._dict_data(data)
        for key in ("tokens", "list", "rows", "items", "rank"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [self._dict_data(row) for row in rows[:limit]]
        return []

    def _upsert_token(
        self,
        *,
        chain_id: str,
        contract_address: str,
        source_rows: Sequence[dict[str, Any]],
    ) -> Token:
        token = self.db.get(Token, (chain_id, contract_address))

        if token is None:
            token = Token(chain_id=chain_id, contract_address=contract_address)

        merged = self._merge_rows(source_rows)
        token.symbol = self._coalesce_string(merged.get("symbol"), token.symbol)
        token.name = self._coalesce_string(merged.get("name"), token.name)
        token.icon_url = self._coalesce_string(
            merged.get("icon")
            or merged.get("logoUrl")
            or merged.get("tokenIconUrl")
            or merged.get("iconUrl"),
            token.icon_url,
        )
        token.decimals = self._coalesce_int(
            merged.get("decimals") or merged.get("tokenDecimals"),
            token.decimals,
        )

        links_value = merged.get("links") or merged.get("link") or merged.get("previewLink")
        if links_value is not None:
            token.links_json = self._json_text(links_value)

        token.updated_at = self._now()
        self.db.add(token)
        return token

    def _store_snapshot(
        self,
        *,
        chain_id: str,
        contract_address: str,
        dynamic_data: dict[str, Any],
        raw_payload: Any,
    ) -> None:
        snapshot = TokenSnapshot(
            chain_id=chain_id,
            contract_address=contract_address,
            price=self._float_value(dynamic_data.get("price") or dynamic_data.get("currentPrice")),
            percent_change_1h=self._float_value(
                dynamic_data.get("percentChange1h") or dynamic_data.get("priceChange1h")
            ),
            percent_change_4h=self._float_value(
                dynamic_data.get("percentChange4h") or dynamic_data.get("priceChange4h")
            ),
            percent_change_24h=self._float_value(
                dynamic_data.get("percentChange24h") or dynamic_data.get("priceChange24h")
            ),
            volume_24h=self._float_value(
                dynamic_data.get("volume24h") or dynamic_data.get("volume")
            ),
            liquidity=self._float_value(dynamic_data.get("liquidity")),
            market_cap=self._float_value(dynamic_data.get("marketCap") or dynamic_data.get("marketcap")),
            fdv=self._float_value(dynamic_data.get("fdv")),
            holders=self._int_value(dynamic_data.get("holders") or dynamic_data.get("holderCount")),
            top10_holders_pct=self._float_value(
                dynamic_data.get("top10HoldersPercentage")
                or dynamic_data.get("holdersTop10Percent")
                or dynamic_data.get("top10HolderRate")
            ),
            kol_holders=self._int_value(dynamic_data.get("kolHolders") or dynamic_data.get("kolHolderCount")),
            kol_holding_pct=self._float_value(
                dynamic_data.get("kolHoldingPercent") or dynamic_data.get("kolHoldingPercentage")
            ),
            smart_money_holding_pct=self._float_value(
                dynamic_data.get("smartMoneyHoldingPercent")
                or dynamic_data.get("smartMoneyHoldingPercentage")
            ),
            raw_json=self._json_text(raw_payload or dynamic_data),
        )
        self.db.add(snapshot)

    def _store_audit(
        self,
        *,
        chain_id: str,
        contract_address: str,
        audit_data: dict[str, Any],
        raw_payload: Any,
    ) -> None:
        extra_info = self._dict_data(audit_data.get("extraInfo"))
        audit = TokenAudit(
            chain_id=chain_id,
            contract_address=contract_address,
            has_result=self._bool_value(audit_data.get("hasResult")),
            is_supported=self._bool_value(audit_data.get("isSupported")),
            risk_level_enum=self._string_value(audit_data.get("riskLevelEnum")),
            risk_level=self._int_value(audit_data.get("riskLevel")),
            buy_tax=self._float_value(extra_info.get("buyTax")),
            sell_tax=self._float_value(extra_info.get("sellTax")),
            is_verified=self._bool_value(extra_info.get("isVerified")),
            risk_items_json=self._json_text(audit_data.get("riskItems")),
            raw_json=self._json_text(raw_payload or audit_data),
        )
        self.db.add(audit)

    def _upsert_signal(
        self,
        *,
        chain_id: str,
        contract_address: str,
        signal_data: dict[str, Any],
    ) -> SmartMoneySignal:
        signal_id = self._string_value(signal_data.get("signalId"))
        statement = select(SmartMoneySignal).where(
            SmartMoneySignal.signal_id == signal_id
        ) if signal_id else select(SmartMoneySignal).where(
            SmartMoneySignal.chain_id == chain_id,
            SmartMoneySignal.contract_address == contract_address,
            SmartMoneySignal.signal_trigger_time
            == self._datetime_from_millis(signal_data.get("signalTriggerTime")),
            SmartMoneySignal.direction == self._string_value(signal_data.get("direction")),
        )

        signal = self.db.execute(statement).scalar_one_or_none()

        if signal is None:
            signal = SmartMoneySignal(
                signal_id=signal_id,
                chain_id=chain_id,
                contract_address=contract_address,
            )

        signal.signal_id = signal_id
        signal.ticker = self._string_value(signal_data.get("ticker"))
        signal.direction = self._string_value(signal_data.get("direction"))
        signal.smart_money_count = self._int_value(signal_data.get("smartMoneyCount"))
        signal.signal_trigger_time = self._datetime_from_millis(signal_data.get("signalTriggerTime"))
        signal.total_token_value = self._float_value(signal_data.get("totalTokenValue"))
        signal.alert_price = self._float_value(signal_data.get("alertPrice"))
        signal.current_price = self._float_value(signal_data.get("currentPrice"))
        signal.highest_price = self._float_value(signal_data.get("highestPrice"))
        signal.exit_rate = self._float_value(signal_data.get("exitRate"))
        signal.status = self._string_value(signal_data.get("status"))
        signal.max_gain = self._float_value(signal_data.get("maxGain"))
        signal.raw_json = self._json_text(signal_data)
        self.db.add(signal)
        return signal

    def _commit_or_recover(self, summary: dict[str, Any]) -> None:
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            summary["errors"].append(f"Database write failed: {exc}")

    def _merge_rows(self, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if value is not None:
                    merged[key] = value
        return merged

    def _dict_data(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list_data(self, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, dict):
            for key in ("list", "rows", "items", "signals", "tokens"):
                nested = value.get(key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]

        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _json_text(self, value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str, separators=(",", ":"))

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _coalesce_string(self, new_value: Any, existing: str | None) -> str | None:
        parsed = self._string_value(new_value)
        return parsed if parsed is not None else existing

    def _coalesce_int(self, new_value: Any, existing: int | None) -> int | None:
        parsed = self._int_value(new_value)
        return parsed if parsed is not None else existing

    def _string_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    def _float_value(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _int_value(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, Decimal):
            return int(value)
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return None
        return None

    def _bool_value(self, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return None

    def _datetime_from_millis(self, value: Any) -> datetime | None:
        timestamp_ms = self._int_value(value)
        if timestamp_ms is None:
            return None
        try:
            return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None


def fetch_token_rows(
    db: Session,
    *,
    chain_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    statement = select(Token)
    if chain_id:
        statement = statement.where(Token.chain_id == chain_id)
    statement = statement.order_by(desc(Token.updated_at)).limit(limit)
    tokens = db.execute(statement).scalars().all()

    rows: list[dict[str, Any]] = []
    for token in tokens:
        latest_snapshot = db.execute(
            select(TokenSnapshot)
            .where(
                TokenSnapshot.chain_id == token.chain_id,
                TokenSnapshot.contract_address == token.contract_address,
            )
            .order_by(desc(TokenSnapshot.ts))
            .limit(1)
        ).scalar_one_or_none()

        latest_audit = db.execute(
            select(TokenAudit)
            .where(
                TokenAudit.chain_id == token.chain_id,
                TokenAudit.contract_address == token.contract_address,
            )
            .order_by(desc(TokenAudit.ts))
            .limit(1)
        ).scalar_one_or_none()

        chain_option = build_chain_option(token.chain_id)
        rows.append(
            {
                "chain_id": token.chain_id,
                "chain_name": chain_option["name"],
                "chain_short_name": chain_option["short_name"],
                "contract_address": token.contract_address,
                "symbol": token.symbol,
                "name": token.name,
                "icon_url": token.icon_url,
                "latest_price": latest_snapshot.price if latest_snapshot else None,
                "latest_percent_change_24h": (
                    latest_snapshot.percent_change_24h if latest_snapshot else None
                ),
                "latest_volume_24h": latest_snapshot.volume_24h if latest_snapshot else None,
                "latest_market_cap": latest_snapshot.market_cap if latest_snapshot else None,
                "holders": latest_snapshot.holders if latest_snapshot else None,
                "risk_level_enum": latest_audit.risk_level_enum if latest_audit else None,
                "risk_level": latest_audit.risk_level if latest_audit else None,
                "latest_snapshot_at": latest_snapshot.ts if latest_snapshot else None,
                "latest_audit_at": latest_audit.ts if latest_audit else None,
                "updated_at": token.updated_at,
            }
        )

    return rows
