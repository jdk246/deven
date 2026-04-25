from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ChatLog,
    KOLCall,
    KOLCallPriceObservation,
    KOLPost,
    KOLProfile,
    KOLTrackRecordScore,
    KOLWallet,
    SmartMoneySignal,
    Token,
    TokenAudit,
    TokenInsight,
    TokenMention,
    TokenSnapshot,
)
from app.schemas import AgentToolResult
from app.services.kol_performance import KOLPerformanceService
from app.services.market_ingestion import SUPPORTED_CHAINS, build_chain_option

SKILL_NAME = "internal_database_context"
TOOL_SOURCE = "internal_context_db"
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


async def get_trending_token_context(
    *,
    db: Session,
    chain_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    input_args = {
        "chain_id": chain_id,
        "limit": safe_limit,
    }
    started_at = time.perf_counter()

    try:
        statement = select(Token)
        if chain_id:
            statement = statement.where(Token.chain_id == chain_id)
        statement = statement.order_by(desc(Token.updated_at)).limit(safe_limit)
        tokens = db.execute(statement).scalars().all()

        items = []
        for token in tokens:
            snapshot = _latest_snapshot(db, chain_id=token.chain_id, contract_address=token.contract_address)
            audit = _latest_audit(db, chain_id=token.chain_id, contract_address=token.contract_address)
            insight = _latest_insight(db, chain_id=token.chain_id, contract_address=token.contract_address)
            mention_summary = _mention_summary(db, chain_id=token.chain_id, contract_address=token.contract_address)
            signal_summary = _signal_summary(db, chain_id=token.chain_id, contract_address=token.contract_address)
            chain_meta = build_chain_option(token.chain_id)

            items.append(
                {
                    "chain_id": token.chain_id,
                    "chain_name": chain_meta["name"],
                    "chain_short_name": chain_meta["short_name"],
                    "contract_address": token.contract_address,
                    "symbol": token.symbol,
                    "name": token.name,
                    "icon_url": token.icon_url,
                    "attention_score": insight.final_score if insight else None,
                    "safety_score": insight.safety_score if insight else None,
                    "insight_label": insight.label if insight else None,
                    "insight_summary": insight.summary if insight else None,
                    "latest_insight_at": _isoformat(insight.ts if insight else None),
                    "price": snapshot.price if snapshot else None,
                    "percent_change_24h": snapshot.percent_change_24h if snapshot else None,
                    "volume_24h": snapshot.volume_24h if snapshot else None,
                    "liquidity": snapshot.liquidity if snapshot else None,
                    "holders": snapshot.holders if snapshot else None,
                    "latest_snapshot_at": _isoformat(snapshot.ts if snapshot else None),
                    "risk_level_enum": audit.risk_level_enum if audit else None,
                    "is_verified": audit.is_verified if audit else None,
                    "latest_audit_at": _isoformat(audit.ts if audit else None),
                    "kol_mention_count": mention_summary["mention_count"],
                    "bullish_mentions": mention_summary["bullish_mentions"],
                    "bearish_mentions": mention_summary["bearish_mentions"],
                    "total_engagement": mention_summary["total_engagement"],
                    "latest_kol_post_at": mention_summary["latest_post_at"],
                    "smart_money_signal_count": signal_summary["signal_count"],
                    "positive_signal_count": signal_summary["positive_signal_count"],
                    "negative_signal_count": signal_summary["negative_signal_count"],
                    "latest_signal_at": signal_summary["latest_signal_at"],
                    "updated_at": _isoformat(token.updated_at),
                }
            )

        data = {
            "items": items,
            "match_count": len(items),
            "available_chains": [
                build_chain_option(supported_chain_id) for supported_chain_id in SUPPORTED_CHAINS
            ],
            "data_mode": get_settings().kol_data_mode,
        }
        return _finalize_result(
            tool_name="get_trending_token_context",
            input_args=input_args,
            data=data,
            started_at=started_at,
            empty=not items,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_trending_token_context",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_token_context(
    *,
    db: Session,
    chain_id: str,
    contract_address: str,
    limit: int = DEFAULT_LIMIT,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    normalized_contract = contract_address.strip()
    input_args = {
        "chain_id": chain_id,
        "contract_address": normalized_contract,
        "limit": safe_limit,
    }
    started_at = time.perf_counter()

    try:
        token = db.get(Token, (chain_id, normalized_contract))
        if token is None:
            return _empty_result(
                tool_name="get_token_context",
                input_args=input_args,
                data={
                    "chain_id": chain_id,
                    "contract_address": normalized_contract,
                    "token": None,
                },
                started_at=started_at,
            )

        snapshot = _latest_snapshot(db, chain_id=chain_id, contract_address=normalized_contract)
        audit = _latest_audit(db, chain_id=chain_id, contract_address=normalized_contract)
        insight = _latest_insight(db, chain_id=chain_id, contract_address=normalized_contract)
        mentions = _recent_token_mentions(
            db,
            chain_id=chain_id,
            contract_address=normalized_contract,
            limit=safe_limit,
        )
        mention_summary = _mention_summary(db, chain_id=chain_id, contract_address=normalized_contract)
        signals = _recent_signals(
            db,
            chain_id=chain_id,
            contract_address=normalized_contract,
            limit=min(10, safe_limit),
        )
        signal_summary = _signal_summary(db, chain_id=chain_id, contract_address=normalized_contract)
        chain_meta = build_chain_option(chain_id)

        data = {
            "token": {
                "chain_id": token.chain_id,
                "chain_name": chain_meta["name"],
                "chain_short_name": chain_meta["short_name"],
                "contract_address": token.contract_address,
                "symbol": token.symbol,
                "name": token.name,
                "icon_url": token.icon_url,
                "decimals": token.decimals,
                "links": _parse_json_text(token.links_json),
                "first_seen_at": _isoformat(token.first_seen_at),
                "updated_at": _isoformat(token.updated_at),
            },
            "latest_market_snapshot": _snapshot_payload(snapshot),
            "latest_audit": _audit_payload(audit),
            "latest_insight": _insight_payload(insight),
            "mention_summary": mention_summary,
            "recent_kol_mentions": mentions,
            "smart_money_summary": signal_summary,
            "recent_smart_money_signals": [_signal_payload(signal) for signal in signals],
            "source_freshness": {
                "market_snapshot_at": _isoformat(snapshot.ts if snapshot else None),
                "audit_at": _isoformat(audit.ts if audit else None),
                "insight_at": _isoformat(insight.ts if insight else None),
                "latest_kol_post_at": mention_summary["latest_post_at"],
                "latest_smart_money_at": signal_summary["latest_signal_at"],
                "kol_data_mode": get_settings().kol_data_mode,
            },
        }
        return _success_result(
            tool_name="get_token_context",
            input_args=input_args,
            data=data,
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_token_context",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def search_kol_mentions(
    *,
    db: Session,
    query: str | None = None,
    chain_id: str | None = None,
    contract_address: str | None = None,
    handle: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    normalized_query = (query or "").strip() or None
    normalized_handle = _normalize_handle(handle)
    normalized_contract = contract_address.strip() if contract_address else None
    input_args = {
        "query": normalized_query,
        "chain_id": chain_id,
        "contract_address": normalized_contract,
        "handle": normalized_handle,
        "limit": safe_limit,
    }
    started_at = time.perf_counter()

    try:
        statement = (
            select(TokenMention, KOLPost, KOLProfile, Token)
            .join(KOLPost, TokenMention.post_id == KOLPost.id)
            .join(KOLProfile, KOLPost.kol_id == KOLProfile.id)
            .outerjoin(
                Token,
                (Token.chain_id == TokenMention.chain_id)
                & (Token.contract_address == TokenMention.contract_address),
            )
        )

        if chain_id:
            statement = statement.where(TokenMention.chain_id == chain_id)

        if normalized_contract:
            statement = statement.where(TokenMention.contract_address == normalized_contract)

        if normalized_handle:
            statement = statement.where(KOLProfile.handle == normalized_handle)

        if normalized_query:
            lowered = normalized_query.lower()
            symbol_probe = lowered.lstrip("$")
            handle_probe = lowered.lstrip("@")
            statement = statement.where(
                or_(
                    func.lower(KOLPost.text).like(f"%{lowered}%"),
                    func.lower(KOLProfile.handle).like(f"%{handle_probe}%"),
                    func.lower(func.coalesce(KOLProfile.display_name, "")).like(f"%{lowered}%"),
                    func.lower(func.coalesce(TokenMention.symbol_text, "")).like(f"%{symbol_probe}%"),
                    func.lower(func.coalesce(Token.contract_address, "")).like(f"%{lowered}%"),
                    func.lower(func.coalesce(Token.symbol, "")).like(f"%{symbol_probe}%"),
                    func.lower(func.coalesce(Token.name, "")).like(f"%{lowered}%"),
                )
            )

        rows = db.execute(
            statement.order_by(
                desc(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)),
                desc(TokenMention.created_at),
            ).limit(safe_limit)
        ).all()

        items = [
            _mention_search_payload(mention, post, profile, token)
            for mention, post, profile, token in rows
        ]

        data = {
            "items": items,
            "match_count": len(items),
            "filters": {
                "query": normalized_query,
                "chain_id": chain_id,
                "contract_address": normalized_contract,
                "handle": normalized_handle,
            },
            "data_mode": get_settings().kol_data_mode,
        }
        return _finalize_result(
            tool_name="search_kol_mentions",
            input_args=input_args,
            data=data,
            started_at=started_at,
            empty=not items,
        )
    except Exception as exc:
        return _error_result(
            tool_name="search_kol_mentions",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_kol_summary(
    *,
    db: Session,
    handle: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    normalized_handle = _normalize_handle(handle)
    input_args = {
        "handle": normalized_handle,
        "limit": safe_limit,
    }
    started_at = time.perf_counter()

    try:
        if normalized_handle:
            profile = db.execute(
                select(KOLProfile).where(KOLProfile.handle == normalized_handle)
            ).scalar_one_or_none()
            if profile is None:
                return _empty_result(
                    tool_name="get_kol_summary",
                    input_args=input_args,
                    data={"handle": normalized_handle, "profile": None},
                    started_at=started_at,
                )

            wallets = db.execute(
                select(KOLWallet)
                .where(KOLWallet.kol_id == profile.id)
                .order_by(desc(KOLWallet.created_at))
            ).scalars().all()
            posts = db.execute(
                select(KOLPost)
                .where(KOLPost.kol_id == profile.id)
                .order_by(desc(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)))
                .limit(safe_limit)
            ).scalars().all()
            mention_rows = db.execute(
                select(TokenMention, KOLPost, Token)
                .join(KOLPost, TokenMention.post_id == KOLPost.id)
                .outerjoin(
                    Token,
                    (Token.chain_id == TokenMention.chain_id)
                    & (Token.contract_address == TokenMention.contract_address),
                )
                .where(KOLPost.kol_id == profile.id)
                .order_by(
                    desc(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)),
                    desc(TokenMention.created_at),
                )
                .limit(safe_limit)
            ).all()

            data = {
                "data_mode": get_settings().kol_data_mode,
                "profile": {
                    "handle": profile.handle,
                    "display_name": profile.display_name,
                    "category": profile.category,
                    "priority": profile.priority,
                    "notes": profile.notes,
                    "created_at": _isoformat(profile.created_at),
                    "updated_at": _isoformat(profile.updated_at),
                },
                "stats": _profile_stats(db, profile.id),
                "wallets": [_wallet_payload(wallet) for wallet in wallets],
                "recent_posts": [_post_payload(post) for post in posts],
                "recent_mentions": [
                    _profile_mention_payload(mention, post, token)
                    for mention, post, token in mention_rows
                ],
            }
            return _success_result(
                tool_name="get_kol_summary",
                input_args=input_args,
                data=data,
                started_at=started_at,
            )

        profiles = db.execute(
            select(KOLProfile)
            .order_by(KOLProfile.priority.asc(), KOLProfile.handle.asc())
            .limit(safe_limit)
        ).scalars().all()

        items = []
        for profile in profiles:
            stats = _profile_stats(db, profile.id)
            items.append(
                {
                    "handle": profile.handle,
                    "display_name": profile.display_name,
                    "category": profile.category,
                    "priority": profile.priority,
                    "stats": stats,
                }
            )

        data = {
            "data_mode": get_settings().kol_data_mode,
            "items": items,
            "match_count": len(items),
        }
        return _finalize_result(
            tool_name="get_kol_summary",
            input_args=input_args,
            data=data,
            started_at=started_at,
            empty=not items,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_kol_summary",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_latest_insight(
    *,
    db: Session,
    chain_id: str,
    contract_address: str,
) -> AgentToolResult:
    normalized_contract = contract_address.strip()
    input_args = {
        "chain_id": chain_id,
        "contract_address": normalized_contract,
    }
    started_at = time.perf_counter()

    try:
        insight = _latest_insight(db, chain_id=chain_id, contract_address=normalized_contract)
        token = db.get(Token, (chain_id, normalized_contract))

        if insight is None:
            return _empty_result(
                tool_name="get_latest_insight",
                input_args=input_args,
                data={
                    "chain_id": chain_id,
                    "contract_address": normalized_contract,
                    "symbol": token.symbol if token else None,
                    "name": token.name if token else None,
                    "insight": None,
                },
                started_at=started_at,
            )

        data = {
            "chain_id": chain_id,
            "contract_address": normalized_contract,
            "symbol": token.symbol if token else None,
            "name": token.name if token else None,
            "insight": _insight_payload(insight),
        }
        return _success_result(
            tool_name="get_latest_insight",
            input_args=input_args,
            data=data,
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_latest_insight",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_high_risk_tokens(
    *,
    db: Session,
    chain_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    input_args = {
        "chain_id": chain_id,
        "limit": safe_limit,
    }
    started_at = time.perf_counter()

    try:
        statement = select(Token)
        if chain_id:
            statement = statement.where(Token.chain_id == chain_id)
        statement = statement.order_by(desc(Token.updated_at))
        tokens = db.execute(statement).scalars().all()

        ranked_items = []
        for token in tokens:
            snapshot = _latest_snapshot(db, chain_id=token.chain_id, contract_address=token.contract_address)
            audit = _latest_audit(db, chain_id=token.chain_id, contract_address=token.contract_address)
            insight = _latest_insight(db, chain_id=token.chain_id, contract_address=token.contract_address)
            risk_flags = _risk_flags(audit=audit, snapshot=snapshot)
            risk_index = _risk_index(audit=audit, insight=insight, snapshot=snapshot)

            if risk_index <= 0 and not risk_flags:
                continue

            chain_meta = build_chain_option(token.chain_id)
            ranked_items.append(
                {
                    "chain_id": token.chain_id,
                    "chain_name": chain_meta["name"],
                    "chain_short_name": chain_meta["short_name"],
                    "contract_address": token.contract_address,
                    "symbol": token.symbol,
                    "name": token.name,
                    "risk_index": risk_index,
                    "safety_score": insight.safety_score if insight else None,
                    "attention_score": insight.final_score if insight else None,
                    "risk_level_enum": audit.risk_level_enum if audit else None,
                    "buy_tax": audit.buy_tax if audit else None,
                    "sell_tax": audit.sell_tax if audit else None,
                    "is_verified": audit.is_verified if audit else None,
                    "liquidity": snapshot.liquidity if snapshot else None,
                    "top10_holders_pct": snapshot.top10_holders_pct if snapshot else None,
                    "risk_flags": risk_flags,
                    "updated_at": _isoformat(token.updated_at),
                }
            )

        ranked_items.sort(
            key=lambda item: (
                float(item.get("risk_index") or 0.0),
                -float(item.get("safety_score") or 100.0),
                float(item.get("attention_score") or 0.0),
            ),
            reverse=True,
        )
        limited_items = ranked_items[:safe_limit]

        data = {
            "items": limited_items,
            "match_count": len(limited_items),
            "data_mode": get_settings().kol_data_mode,
        }
        return _finalize_result(
            tool_name="get_high_risk_tokens",
            input_args=input_args,
            data=data,
            started_at=started_at,
            empty=not limited_items,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_high_risk_tokens",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_data_mode_status(
    *,
    db: Session,
) -> AgentToolResult:
    input_args: dict[str, Any] = {}
    started_at = time.perf_counter()

    try:
        settings = get_settings()
        counts = {
            "tokens": _count_rows(db, Token),
            "token_snapshots": _count_rows(db, TokenSnapshot),
            "token_audits": _count_rows(db, TokenAudit),
            "smart_money_signals": _count_rows(db, SmartMoneySignal),
            "kol_profiles": _count_rows(db, KOLProfile),
            "kol_wallets": _count_rows(db, KOLWallet),
            "kol_posts": _count_rows(db, KOLPost),
            "token_mentions": _count_rows(db, TokenMention),
            "token_insights": _count_rows(db, TokenInsight),
            "chat_logs": _count_rows(db, ChatLog),
            "kol_calls": _count_rows(db, KOLCall),
            "evaluated_kol_calls": int(
                db.execute(
                    select(func.count())
                    .select_from(KOLCallPriceObservation)
                    .where(KOLCallPriceObservation.evaluation_status == "evaluated")
                ).scalar_one()
                or 0
            ),
            "kol_track_record_scores": _count_rows(db, KOLTrackRecordScore),
        }
        data = {
            "kol_data_mode": settings.kol_data_mode,
            "enabled_chains": [build_chain_option(chain_value) for chain_value in settings.enabled_chains],
            "supported_chains": [
                build_chain_option(chain_value) for chain_value in SUPPORTED_CHAINS
            ],
            "record_counts": counts,
            "latest_timestamps": {
                "tokens_updated_at": _isoformat(
                    db.execute(select(func.max(Token.updated_at))).scalar_one_or_none()
                ),
                "snapshot_at": _isoformat(
                    db.execute(select(func.max(TokenSnapshot.ts))).scalar_one_or_none()
                ),
                "audit_at": _isoformat(
                    db.execute(select(func.max(TokenAudit.ts))).scalar_one_or_none()
                ),
                "smart_money_at": _isoformat(
                    db.execute(
                        select(func.max(func.coalesce(SmartMoneySignal.signal_trigger_time, SmartMoneySignal.ts)))
                    ).scalar_one_or_none()
                ),
                "kol_post_at": _isoformat(
                    db.execute(
                        select(func.max(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)))
                    ).scalar_one_or_none()
                ),
                "insight_at": _isoformat(
                    db.execute(select(func.max(TokenInsight.ts))).scalar_one_or_none()
                ),
            },
        }
        return _success_result(
            tool_name="get_data_mode_status",
            input_args=input_args,
            data=data,
            started_at=started_at,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_data_mode_status",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def rank_kols_by_track_record(
    *,
    db: Session,
    limit: int = DEFAULT_LIMIT,
    min_evaluated_calls: int | None = None,
    include_insufficient: bool = True,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    safe_min_calls = None if min_evaluated_calls is None else max(0, int(min_evaluated_calls))
    input_args = {
        "limit": safe_limit,
        "min_evaluated_calls": safe_min_calls,
        "include_insufficient": include_insufficient,
    }
    started_at = time.perf_counter()

    try:
        payload = KOLPerformanceService(db).list_rankings(
            limit=safe_limit,
            min_evaluated_calls=safe_min_calls,
            include_insufficient=include_insufficient,
        )
        items = payload.get("items") if isinstance(payload, dict) else None
        return _finalize_result(
            tool_name="rank_kols_by_track_record",
            input_args=input_args,
            data=payload,
            started_at=started_at,
            empty=not isinstance(items, list) or not items,
        )
    except Exception as exc:
        return _error_result(
            tool_name="rank_kols_by_track_record",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_kol_track_record(
    *,
    db: Session,
    handle: str,
) -> AgentToolResult:
    normalized_handle = _normalize_handle(handle)
    input_args = {
        "handle": normalized_handle,
    }
    started_at = time.perf_counter()

    try:
        payload = KOLPerformanceService(db).get_track_record(handle=normalized_handle or "")
        if payload is None:
            return _empty_result(
                tool_name="get_kol_track_record",
                input_args=input_args,
                data={"handle": normalized_handle, "profile": None},
                started_at=started_at,
            )

        score = payload.get("score") if isinstance(payload, dict) else None
        recent_calls = payload.get("recent_calls") if isinstance(payload, dict) else None
        is_empty = not score and not recent_calls
        return _finalize_result(
            tool_name="get_kol_track_record",
            input_args=input_args,
            data=payload,
            started_at=started_at,
            empty=is_empty,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_kol_track_record",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


async def get_kol_call_examples(
    *,
    db: Session,
    handle: str | None = None,
    symbol: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> AgentToolResult:
    safe_limit = _clamp_limit(limit)
    normalized_handle = _normalize_handle(handle)
    normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) and symbol.strip() else None
    input_args = {
        "handle": normalized_handle,
        "symbol": normalized_symbol,
        "limit": safe_limit,
    }
    started_at = time.perf_counter()

    try:
        payload = KOLPerformanceService(db).get_call_examples(
            handle=normalized_handle,
            symbol=normalized_symbol,
            limit=safe_limit,
        )
        items = payload.get("items") if isinstance(payload, dict) else None
        return _finalize_result(
            tool_name="get_kol_call_examples",
            input_args=input_args,
            data=payload,
            started_at=started_at,
            empty=not isinstance(items, list) or not items,
        )
    except Exception as exc:
        return _error_result(
            tool_name="get_kol_call_examples",
            input_args=input_args,
            error=str(exc),
            started_at=started_at,
        )


def _success_result(
    *,
    tool_name: str,
    input_args: dict[str, Any],
    data: Any,
    started_at: float,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=SKILL_NAME,
        tool_name=tool_name,
        input_args=_jsonable(input_args),
        source=TOOL_SOURCE,
        status="ok",
        latency_ms=_latency_ms(started_at),
        fetched_at=_now(),
        data=_jsonable(data),
        error=None,
    )


def _empty_result(
    *,
    tool_name: str,
    input_args: dict[str, Any],
    data: Any,
    started_at: float,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=SKILL_NAME,
        tool_name=tool_name,
        input_args=_jsonable(input_args),
        source=TOOL_SOURCE,
        status="empty",
        latency_ms=_latency_ms(started_at),
        fetched_at=_now(),
        data=_jsonable(data),
        error=None,
    )


def _finalize_result(
    *,
    tool_name: str,
    input_args: dict[str, Any],
    data: Any,
    started_at: float,
    empty: bool,
) -> AgentToolResult:
    if empty:
        return _empty_result(
            tool_name=tool_name,
            input_args=input_args,
            data=data,
            started_at=started_at,
        )
    return _success_result(
        tool_name=tool_name,
        input_args=input_args,
        data=data,
        started_at=started_at,
    )


def _error_result(
    *,
    tool_name: str,
    input_args: dict[str, Any],
    error: str,
    started_at: float,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=SKILL_NAME,
        tool_name=tool_name,
        input_args=_jsonable(input_args),
        source=TOOL_SOURCE,
        status="error",
        latency_ms=_latency_ms(started_at),
        fetched_at=_now(),
        data=None,
        error=error,
    )


def _latest_snapshot(db: Session, *, chain_id: str, contract_address: str) -> TokenSnapshot | None:
    return db.execute(
        select(TokenSnapshot)
        .where(
            TokenSnapshot.chain_id == chain_id,
            TokenSnapshot.contract_address == contract_address,
        )
        .order_by(desc(TokenSnapshot.ts))
        .limit(1)
    ).scalar_one_or_none()


def _latest_audit(db: Session, *, chain_id: str, contract_address: str) -> TokenAudit | None:
    return db.execute(
        select(TokenAudit)
        .where(
            TokenAudit.chain_id == chain_id,
            TokenAudit.contract_address == contract_address,
        )
        .order_by(desc(TokenAudit.ts))
        .limit(1)
    ).scalar_one_or_none()


def _latest_insight(db: Session, *, chain_id: str, contract_address: str) -> TokenInsight | None:
    return db.execute(
        select(TokenInsight)
        .where(
            TokenInsight.chain_id == chain_id,
            TokenInsight.contract_address == contract_address,
        )
        .order_by(desc(TokenInsight.ts))
        .limit(1)
    ).scalar_one_or_none()


def _recent_signals(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
    limit: int,
) -> list[SmartMoneySignal]:
    return db.execute(
        select(SmartMoneySignal)
        .where(
            SmartMoneySignal.chain_id == chain_id,
            SmartMoneySignal.contract_address == contract_address,
        )
        .order_by(
            desc(func.coalesce(SmartMoneySignal.signal_trigger_time, SmartMoneySignal.ts)),
            desc(SmartMoneySignal.ts),
        )
        .limit(limit)
    ).scalars().all()


def _recent_token_mentions(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(TokenMention, KOLPost, KOLProfile)
        .join(KOLPost, TokenMention.post_id == KOLPost.id)
        .join(KOLProfile, KOLPost.kol_id == KOLProfile.id)
        .where(
            TokenMention.chain_id == chain_id,
            TokenMention.contract_address == contract_address,
        )
        .order_by(desc(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)))
        .limit(limit)
    ).all()

    return [
        {
            "handle": profile.handle,
            "display_name": profile.display_name,
            "category": profile.category,
            "priority": profile.priority,
            "mention_type": mention.mention_type,
            "symbol_text": mention.symbol_text,
            "is_resolved": mention.is_resolved,
            "confidence": mention.confidence,
            "sentiment": post.sentiment,
            "source_mode": post.source_mode,
            "created_at": _isoformat(post.created_at or post.inserted_at),
            "text": post.text,
            "url": post.url,
            "engagement": {
                "like_count": post.like_count,
                "repost_count": post.repost_count,
                "reply_count": post.reply_count,
                "view_count": post.view_count,
            },
        }
        for mention, post, profile in rows
    ]


def _mention_summary(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
) -> dict[str, Any]:
    rows = db.execute(
        select(TokenMention, KOLPost)
        .join(KOLPost, TokenMention.post_id == KOLPost.id)
        .where(
            TokenMention.chain_id == chain_id,
            TokenMention.contract_address == contract_address,
        )
        .order_by(desc(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)))
    ).all()

    seen_post_ids: set[int] = set()
    bullish_mentions = 0
    bearish_mentions = 0
    neutral_mentions = 0
    unknown_mentions = 0
    total_engagement = 0
    latest_post_at: datetime | None = None

    for _, post in rows:
        if post.id in seen_post_ids:
            continue
        seen_post_ids.add(post.id)
        sentiment = (post.sentiment or "unknown").strip().lower()
        if sentiment == "bullish":
            bullish_mentions += 1
        elif sentiment == "bearish":
            bearish_mentions += 1
        elif sentiment == "neutral":
            neutral_mentions += 1
        else:
            unknown_mentions += 1
        total_engagement += _engagement_total(post)
        post_time = post.created_at or post.inserted_at
        if post_time and (latest_post_at is None or _to_utc(post_time) > _to_utc(latest_post_at)):
            latest_post_at = post_time

    return {
        "mention_count": len(seen_post_ids),
        "bullish_mentions": bullish_mentions,
        "bearish_mentions": bearish_mentions,
        "neutral_mentions": neutral_mentions,
        "unknown_mentions": unknown_mentions,
        "total_engagement": total_engagement,
        "latest_post_at": _isoformat(latest_post_at),
    }


def _signal_summary(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
) -> dict[str, Any]:
    signals = _recent_signals(
        db,
        chain_id=chain_id,
        contract_address=contract_address,
        limit=MAX_LIMIT,
    )

    positive = 0
    negative = 0
    latest_signal_at: datetime | None = None
    for signal in signals:
        direction = (signal.direction or "").strip().lower()
        if direction in {"buy", "long", "accumulate", "bullish"}:
            positive += 1
        elif direction in {"sell", "short", "exit", "bearish"}:
            negative += 1
        signal_time = signal.signal_trigger_time or signal.ts
        if signal_time and (latest_signal_at is None or _to_utc(signal_time) > _to_utc(latest_signal_at)):
            latest_signal_at = signal_time

    return {
        "signal_count": len(signals),
        "positive_signal_count": positive,
        "negative_signal_count": negative,
        "latest_signal_at": _isoformat(latest_signal_at),
    }


def _profile_stats(db: Session, profile_id: int) -> dict[str, Any]:
    posts = db.execute(
        select(KOLPost)
        .where(KOLPost.kol_id == profile_id)
        .order_by(desc(func.coalesce(KOLPost.created_at, KOLPost.inserted_at)))
    ).scalars().all()

    bullish_posts = 0
    bearish_posts = 0
    neutral_posts = 0
    unknown_posts = 0
    total_engagement = 0
    latest_post_at: datetime | None = None

    for post in posts:
        sentiment = (post.sentiment or "unknown").strip().lower()
        if sentiment == "bullish":
            bullish_posts += 1
        elif sentiment == "bearish":
            bearish_posts += 1
        elif sentiment == "neutral":
            neutral_posts += 1
        else:
            unknown_posts += 1
        total_engagement += _engagement_total(post)
        post_time = post.created_at or post.inserted_at
        if post_time and (latest_post_at is None or _to_utc(post_time) > _to_utc(latest_post_at)):
            latest_post_at = post_time

    resolved_mentions = int(
        db.execute(
            select(func.count())
            .select_from(TokenMention)
            .join(KOLPost, TokenMention.post_id == KOLPost.id)
            .where(
                KOLPost.kol_id == profile_id,
                TokenMention.is_resolved.is_(True),
            )
        ).scalar_one()
        or 0
    )
    wallet_count = int(
        db.execute(
            select(func.count())
            .select_from(KOLWallet)
            .where(KOLWallet.kol_id == profile_id)
        ).scalar_one()
        or 0
    )
    unique_tokens_mentioned = int(
        db.execute(
            select(func.count(func.distinct(TokenMention.contract_address)))
            .select_from(TokenMention)
            .join(KOLPost, TokenMention.post_id == KOLPost.id)
            .where(
                KOLPost.kol_id == profile_id,
                TokenMention.is_resolved.is_(True),
                TokenMention.contract_address.is_not(None),
            )
        ).scalar_one()
        or 0
    )

    return {
        "post_count": len(posts),
        "resolved_mention_count": resolved_mentions,
        "wallet_count": wallet_count,
        "unique_tokens_mentioned": unique_tokens_mentioned,
        "bullish_posts": bullish_posts,
        "bearish_posts": bearish_posts,
        "neutral_posts": neutral_posts,
        "unknown_posts": unknown_posts,
        "total_engagement": total_engagement,
        "latest_post_at": _isoformat(latest_post_at),
    }


def _wallet_payload(wallet: KOLWallet) -> dict[str, Any]:
    return {
        "chain_id": wallet.chain_id,
        "chain_name": build_chain_option(wallet.chain_id)["name"],
        "address": wallet.address,
        "source_type": wallet.source_type,
        "source_url": wallet.source_url,
        "confidence": wallet.confidence,
        "created_at": _isoformat(wallet.created_at),
    }


def _post_payload(post: KOLPost) -> dict[str, Any]:
    return {
        "external_post_id": post.external_post_id,
        "created_at": _isoformat(post.created_at or post.inserted_at),
        "text": post.text,
        "url": post.url,
        "like_count": post.like_count,
        "repost_count": post.repost_count,
        "reply_count": post.reply_count,
        "view_count": post.view_count,
        "source_mode": post.source_mode,
        "sentiment": post.sentiment,
        "sentiment_score": post.sentiment_score,
    }


def _profile_mention_payload(
    mention: TokenMention,
    post: KOLPost,
    token: Token | None,
) -> dict[str, Any]:
    chain_name = build_chain_option(mention.chain_id)["name"] if mention.chain_id else None
    return {
        "post_created_at": _isoformat(post.created_at or post.inserted_at),
        "chain_id": mention.chain_id,
        "chain_name": chain_name,
        "contract_address": mention.contract_address,
        "symbol_text": mention.symbol_text,
        "mention_type": mention.mention_type,
        "is_resolved": mention.is_resolved,
        "confidence": mention.confidence,
        "token_symbol": token.symbol if token else None,
        "token_name": token.name if token else None,
        "sentiment": post.sentiment,
        "text": post.text,
        "url": post.url,
    }


def _mention_search_payload(
    mention: TokenMention,
    post: KOLPost,
    profile: KOLProfile,
    token: Token | None,
) -> dict[str, Any]:
    chain_name = build_chain_option(mention.chain_id)["name"] if mention.chain_id else None
    return {
        "handle": profile.handle,
        "display_name": profile.display_name,
        "category": profile.category,
        "priority": profile.priority,
        "post_created_at": _isoformat(post.created_at or post.inserted_at),
        "text": post.text,
        "url": post.url,
        "source_mode": post.source_mode,
        "sentiment": post.sentiment,
        "engagement": {
            "like_count": post.like_count,
            "repost_count": post.repost_count,
            "reply_count": post.reply_count,
            "view_count": post.view_count,
        },
        "mention_type": mention.mention_type,
        "symbol_text": mention.symbol_text,
        "is_resolved": mention.is_resolved,
        "confidence": mention.confidence,
        "chain_id": mention.chain_id,
        "chain_name": chain_name,
        "contract_address": mention.contract_address,
        "token_symbol": token.symbol if token else None,
        "token_name": token.name if token else None,
    }


def _snapshot_payload(snapshot: TokenSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "ts": _isoformat(snapshot.ts),
        "price": snapshot.price,
        "percent_change_1h": snapshot.percent_change_1h,
        "percent_change_4h": snapshot.percent_change_4h,
        "percent_change_24h": snapshot.percent_change_24h,
        "volume_24h": snapshot.volume_24h,
        "liquidity": snapshot.liquidity,
        "market_cap": snapshot.market_cap,
        "fdv": snapshot.fdv,
        "holders": snapshot.holders,
        "top10_holders_pct": snapshot.top10_holders_pct,
        "kol_holders": snapshot.kol_holders,
        "kol_holding_pct": snapshot.kol_holding_pct,
        "smart_money_holding_pct": snapshot.smart_money_holding_pct,
    }


def _audit_payload(audit: TokenAudit | None) -> dict[str, Any] | None:
    if audit is None:
        return None
    return {
        "ts": _isoformat(audit.ts),
        "has_result": audit.has_result,
        "is_supported": audit.is_supported,
        "risk_level_enum": audit.risk_level_enum,
        "risk_level": audit.risk_level,
        "buy_tax": audit.buy_tax,
        "sell_tax": audit.sell_tax,
        "is_verified": audit.is_verified,
        "risk_items": _parse_json_text(audit.risk_items_json),
    }


def _insight_payload(insight: TokenInsight | None) -> dict[str, Any] | None:
    if insight is None:
        return None
    rationale = _parse_json_text(insight.rationale_json) or {}
    return {
        "market_score": insight.market_score,
        "kol_score": insight.kol_score,
        "smart_money_score": insight.smart_money_score,
        "safety_score": insight.safety_score,
        "attention_score": insight.final_score,
        "label": insight.label,
        "summary": insight.summary,
        "generated_at": _isoformat(insight.ts),
        "rationale": rationale,
    }


def _signal_payload(signal: SmartMoneySignal) -> dict[str, Any]:
    return {
        "signal_id": signal.signal_id,
        "chain_id": signal.chain_id,
        "contract_address": signal.contract_address,
        "ticker": signal.ticker,
        "direction": signal.direction,
        "smart_money_count": signal.smart_money_count,
        "signal_trigger_time": _isoformat(signal.signal_trigger_time),
        "total_token_value": signal.total_token_value,
        "alert_price": signal.alert_price,
        "current_price": signal.current_price,
        "highest_price": signal.highest_price,
        "exit_rate": signal.exit_rate,
        "status": signal.status,
        "max_gain": signal.max_gain,
        "ts": _isoformat(signal.ts),
    }


def _risk_index(
    *,
    audit: TokenAudit | None,
    insight: TokenInsight | None,
    snapshot: TokenSnapshot | None,
) -> float:
    risk_value = 0.0

    if insight and insight.safety_score is not None:
        risk_value = max(risk_value, 100.0 - float(insight.safety_score))

    if audit is not None:
        risk_level = (audit.risk_level_enum or "").strip().lower()
        if risk_level == "high":
            risk_value += 40.0
        elif risk_level == "medium":
            risk_value += 20.0
        elif risk_level == "low":
            risk_value += 5.0

        if audit.is_verified is False:
            risk_value += 12.0

        buy_tax_pct = _percent(audit.buy_tax)
        if buy_tax_pct is not None and buy_tax_pct > 5.0:
            risk_value += min(20.0, buy_tax_pct)

        sell_tax_pct = _percent(audit.sell_tax)
        if sell_tax_pct is not None and sell_tax_pct > 5.0:
            risk_value += min(20.0, sell_tax_pct)

    if snapshot is not None:
        concentration_pct = _percent(snapshot.top10_holders_pct)
        if concentration_pct is not None and concentration_pct > 80.0:
            risk_value += 20.0
        elif concentration_pct is not None and concentration_pct > 60.0:
            risk_value += 10.0

        if snapshot.liquidity is not None and snapshot.liquidity < 100_000.0:
            risk_value += 15.0
        elif snapshot.liquidity is not None and snapshot.liquidity < 250_000.0:
            risk_value += 8.0

    return round(min(risk_value, 100.0), 2)


def _risk_flags(
    *,
    audit: TokenAudit | None,
    snapshot: TokenSnapshot | None,
) -> list[str]:
    flags: list[str] = []

    if audit is None or audit.has_result is False:
        flags.append("audit coverage is unavailable")
    else:
        risk_level = (audit.risk_level_enum or "").strip().lower()
        if risk_level == "high":
            flags.append("high audit risk")
        elif risk_level == "medium":
            flags.append("medium audit risk")

        if audit.is_verified is False:
            flags.append("contract verification is missing")

        buy_tax_pct = _percent(audit.buy_tax)
        if buy_tax_pct is not None and buy_tax_pct > 5.0:
            flags.append(f"buy tax is elevated at {buy_tax_pct:.1f}%")

        sell_tax_pct = _percent(audit.sell_tax)
        if sell_tax_pct is not None and sell_tax_pct > 5.0:
            flags.append(f"sell tax is elevated at {sell_tax_pct:.1f}%")

    if snapshot is not None:
        concentration_pct = _percent(snapshot.top10_holders_pct)
        if concentration_pct is not None and concentration_pct > 80.0:
            flags.append("holder concentration is very high")
        elif concentration_pct is not None and concentration_pct > 60.0:
            flags.append("holder concentration is elevated")

        if snapshot.liquidity is not None and snapshot.liquidity < 100_000.0:
            flags.append("liquidity is on the lighter side")

    return flags


def _count_rows(db: Session, model: type[Any]) -> int:
    return int(db.execute(select(func.count()).select_from(model)).scalar_one() or 0)


def _clamp_limit(value: int) -> int:
    return max(1, min(int(value), MAX_LIMIT))


def _normalize_handle(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lstrip("@").lower()
    return normalized or None


def _engagement_total(post: KOLPost) -> int:
    return int(
        (post.like_count or 0)
        + (post.repost_count or 0)
        + (post.reply_count or 0)
        + (post.view_count or 0)
    )


def _percent(value: float | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if 0.0 <= abs(numeric) <= 1.0:
        return numeric * 100.0
    return numeric


def _parse_json_text(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


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


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _to_utc(value).isoformat().replace("+00:00", "Z")


def _now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "get_data_mode_status",
    "get_high_risk_tokens",
    "get_kol_call_examples",
    "get_kol_track_record",
    "get_kol_summary",
    "get_latest_insight",
    "get_token_context",
    "get_trending_token_context",
    "rank_kols_by_track_record",
    "search_kol_mentions",
]
