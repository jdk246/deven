from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    KOLPost,
    KOLProfile,
    KOLWallet,
    KOLWalletPosition,
    SmartMoneySignal,
    Token,
    TokenAudit,
    TokenInsight,
    TokenMention,
    TokenSnapshot,
)
from app.services.insight_generation import InsightGenerationService
from app.services.market_ingestion import SUPPORTED_CHAINS, build_chain_option
from app.services.market_ingestion import fetch_token_rows as fetch_legacy_token_rows
from app.services.scoring import ScoringService


def fetch_token_rows(
    db: Session,
    *,
    chain_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    return fetch_legacy_token_rows(db, chain_id=chain_id, limit=limit)


def build_trending_token_payload(
    db: Session,
    *,
    chain_id: str | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    statement = select(Token)
    if chain_id:
        statement = statement.where(Token.chain_id == chain_id)
    statement = statement.order_by(desc(Token.updated_at)).limit(limit)
    tokens = db.execute(statement).scalars().all()

    items = [_build_trending_item(db, token) for token in tokens]
    return {
        "items": items,
        "available_chains": [build_chain_option(supported_chain_id) for supported_chain_id in SUPPORTED_CHAINS],
    }


def build_token_detail_payload(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
) -> dict[str, Any] | None:
    token = db.get(Token, (chain_id, contract_address))
    if token is None:
        return None

    snapshot = _latest_snapshot(db, chain_id=chain_id, contract_address=contract_address)
    audit = _latest_audit(db, chain_id=chain_id, contract_address=contract_address)
    signals = _smart_money_signals(db, chain_id=chain_id, contract_address=contract_address, limit=20)
    kol_mentions = _kol_mentions_for_token(
        db,
        chain_id=chain_id,
        contract_address=contract_address,
        limit=50,
    )
    insight = _insight_payload(db, chain_id=chain_id, contract_address=contract_address)

    chain_meta = build_chain_option(chain_id)
    return {
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
        "latest_market": _snapshot_payload(snapshot),
        "audit": _audit_payload(audit),
        "smart_money_signals": [_smart_money_payload(signal) for signal in signals],
        "kol_mentions": kol_mentions,
        "insight": insight,
        "source_freshness": {
            "market_snapshot_at": _isoformat(snapshot.ts if snapshot else None),
            "audit_at": _isoformat(audit.ts if audit else None),
            "latest_smart_money_at": _isoformat(_latest_signal_time(signals)),
            "latest_kol_post_at": _isoformat(_latest_kol_post_time_from_mentions(kol_mentions)),
            "insight_at": _isoformat(insight.get("generated_at") if insight else None),
            "kol_data_mode": get_settings().kol_data_mode,
        },
    }


def build_kol_list_payload(db: Session) -> dict[str, Any]:
    profiles = db.execute(select(KOLProfile).order_by(KOLProfile.priority.asc(), KOLProfile.handle.asc())).scalars().all()
    items = []

    for profile in profiles:
        post_count = int(
            db.execute(
                select(func.count()).select_from(KOLPost).where(KOLPost.kol_id == profile.id)
            ).scalar_one()
            or 0
        )
        resolved_mention_count = int(
            db.execute(
                select(func.count())
                .select_from(TokenMention)
                .join(KOLPost, TokenMention.post_id == KOLPost.id)
                .where(
                    KOLPost.kol_id == profile.id,
                    TokenMention.is_resolved.is_(True),
                )
            ).scalar_one()
            or 0
        )
        wallet_count = int(
            db.execute(
                select(func.count()).select_from(KOLWallet).where(KOLWallet.kol_id == profile.id)
            ).scalar_one()
            or 0
        )
        items.append(
            {
                "handle": profile.handle,
                "display_name": profile.display_name,
                "category": profile.category,
                "priority": profile.priority,
                "post_count": post_count,
                "resolved_mention_count": resolved_mention_count,
                "wallet_count": wallet_count,
            }
        )

    return {
        "data_mode": get_settings().kol_data_mode,
        "items": items,
    }


def build_kol_feed_payload(
    db: Session,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    rows = db.execute(
        select(KOLPost, KOLProfile)
        .join(KOLProfile, KOLPost.kol_id == KOLProfile.id)
        .order_by(desc(KOLPost.created_at), desc(KOLPost.inserted_at))
        .limit(limit)
    ).all()

    items = []
    for post, profile in rows:
        mentions = db.execute(
            select(TokenMention)
            .where(TokenMention.post_id == post.id)
            .order_by(desc(TokenMention.created_at))
        ).scalars().all()

        items.append(
            {
                "post_id": post.id,
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
                "kol": {
                    "handle": profile.handle,
                    "display_name": profile.display_name,
                    "category": profile.category,
                    "priority": profile.priority,
                },
                "resolved_mention_count": sum(1 for mention in mentions if mention.is_resolved),
                "mentions": [
                    {
                        "mention_type": mention.mention_type,
                        "symbol_text": mention.symbol_text,
                        "chain_id": mention.chain_id,
                        "chain_name": build_chain_option(mention.chain_id)["name"] if mention.chain_id else None,
                        "contract_address": mention.contract_address,
                        "is_resolved": mention.is_resolved,
                        "confidence": mention.confidence,
                    }
                    for mention in mentions[:5]
                ],
            }
        )

    return {
        "data_mode": get_settings().kol_data_mode,
        "items": items,
    }


def build_kol_detail_payload(
    db: Session,
    *,
    handle: str,
) -> dict[str, Any] | None:
    normalized_handle = handle.lstrip("@").strip().lower()
    profile = db.execute(
        select(KOLProfile).where(KOLProfile.handle == normalized_handle)
    ).scalar_one_or_none()
    if profile is None:
        return None

    wallets = db.execute(
        select(KOLWallet).where(KOLWallet.kol_id == profile.id).order_by(KOLWallet.created_at.desc())
    ).scalars().all()
    posts = db.execute(
        select(KOLPost)
        .where(KOLPost.kol_id == profile.id)
        .order_by(desc(KOLPost.created_at), desc(KOLPost.inserted_at))
        .limit(20)
    ).scalars().all()
    mentions = db.execute(
        select(TokenMention, KOLPost)
        .join(KOLPost, TokenMention.post_id == KOLPost.id)
        .where(KOLPost.kol_id == profile.id)
        .order_by(desc(KOLPost.created_at), desc(TokenMention.created_at))
        .limit(50)
    ).all()

    return {
        "profile": {
            "handle": profile.handle,
            "display_name": profile.display_name,
            "category": profile.category,
            "priority": profile.priority,
            "notes": profile.notes,
            "created_at": _isoformat(profile.created_at),
            "updated_at": _isoformat(profile.updated_at),
            "data_mode": get_settings().kol_data_mode,
        },
        "wallets": [
            {
                "chain_id": wallet.chain_id,
                "chain_name": build_chain_option(wallet.chain_id)["name"],
                "address": wallet.address,
                "source_type": wallet.source_type,
                "source_url": wallet.source_url,
                "confidence": wallet.confidence,
                "created_at": _isoformat(wallet.created_at),
            }
            for wallet in wallets
        ],
        "recent_posts": [
            {
                "id": post.id,
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
                "resolved_mention_count": int(
                    db.execute(
                        select(func.count())
                        .select_from(TokenMention)
                        .where(
                            TokenMention.post_id == post.id,
                            TokenMention.is_resolved.is_(True),
                        )
                    ).scalar_one()
                    or 0
                ),
            }
            for post in posts
        ],
        "mentions": [
            _kol_detail_mention_payload(db, mention, post)
            for mention, post in mentions
        ],
    }


def build_insight_list_payload(
    db: Session,
    *,
    chain_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    statement = select(Token)
    if chain_id:
        statement = statement.where(Token.chain_id == chain_id)
    statement = statement.order_by(desc(Token.updated_at)).limit(limit)
    tokens = db.execute(statement).scalars().all()

    items = []
    for token in tokens:
        insight = _insight_payload(
            db,
            chain_id=token.chain_id,
            contract_address=token.contract_address,
        )
        if insight is None:
            continue

        items.append(
            {
                "chain_id": token.chain_id,
                "chain_name": build_chain_option(token.chain_id)["name"],
                "contract_address": token.contract_address,
                "symbol": token.symbol,
                "name": token.name,
                "market_score": insight.get("market_score"),
                "kol_score": insight.get("kol_score"),
                "smart_money_score": insight.get("smart_money_score"),
                "safety_score": insight.get("safety_score"),
                "final_score": insight.get("final_score"),
                "attention_score": insight.get("attention_score"),
                "label": insight.get("label"),
                "summary": insight.get("summary"),
                "updated_at": _isoformat(insight.get("generated_at")),
            }
        )

    return {"items": items}


def build_chat_response(
    db: Session,
    *,
    message: str,
    chain_id: str | None = None,
) -> dict[str, Any]:
    from app.services.chat_agent import ChatAgentService

    return ChatAgentService(db).answer_question(
        message=message,
        chain_id=chain_id,
    )


def _build_trending_item(db: Session, token: Token) -> dict[str, Any]:
    snapshot = _latest_snapshot(db, chain_id=token.chain_id, contract_address=token.contract_address)
    audit = _latest_audit(db, chain_id=token.chain_id, contract_address=token.contract_address)
    chain_meta = build_chain_option(token.chain_id)

    mention_count = int(
        db.execute(
            select(func.count(distinct(TokenMention.post_id))).where(
                TokenMention.chain_id == token.chain_id,
                TokenMention.contract_address == token.contract_address,
                TokenMention.is_resolved.is_(True),
            )
        ).scalar_one()
        or 0
    )
    smart_money_signal_count = int(
        db.execute(
            select(func.count()).select_from(SmartMoneySignal).where(
                SmartMoneySignal.chain_id == token.chain_id,
                SmartMoneySignal.contract_address == token.contract_address,
            )
        ).scalar_one()
        or 0
    )

    insight = _insight_payload(db, chain_id=token.chain_id, contract_address=token.contract_address)
    if insight is None:
        score_breakdown = ScoringService(db).score_token(
            chain_id=token.chain_id,
            contract_address=token.contract_address,
            persist=False,
        )
        attention_score = score_breakdown.attention_score
        label = score_breakdown.label
    else:
        attention_score = insight.get("attention_score")
        label = insight.get("label")

    return {
        "chain_id": token.chain_id,
        "chain_name": chain_meta["name"],
        "chain_short_name": chain_meta["short_name"],
        "contract_address": token.contract_address,
        "symbol": token.symbol,
        "name": token.name,
        "icon_url": token.icon_url,
        "price": snapshot.price if snapshot else None,
        "percent_change_24h": snapshot.percent_change_24h if snapshot else None,
        "volume_24h": snapshot.volume_24h if snapshot else None,
        "liquidity": snapshot.liquidity if snapshot else None,
        "holders": snapshot.holders if snapshot else None,
        "risk_level_enum": audit.risk_level_enum if audit else None,
        "kol_mention_count": mention_count,
        "smart_money_signal_count": smart_money_signal_count,
        "attention_score": attention_score,
        "label": label,
        "updated_at": _isoformat(token.updated_at),
    }


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


def _smart_money_signals(
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
        .order_by(desc(SmartMoneySignal.signal_trigger_time), desc(SmartMoneySignal.ts))
        .limit(limit)
    ).scalars().all()


def _kol_mentions_for_token(
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
            TokenMention.is_resolved.is_(True),
        )
        .order_by(desc(KOLPost.created_at), desc(KOLPost.inserted_at))
        .limit(limit)
    ).all()

    items = []
    for mention, post, profile in rows:
        items.append(
            {
                "handle": profile.handle,
                "display_name": profile.display_name,
                "category": profile.category,
                "priority": profile.priority,
                "mention_type": mention.mention_type,
                "symbol_text": mention.symbol_text,
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
        )

    return items


def _insight_payload(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
) -> dict[str, Any] | None:
    stored_insight = _latest_insight(db, chain_id=chain_id, contract_address=contract_address)
    if stored_insight is not None:
        rationale = _parse_json_text(stored_insight.rationale_json) or {}
        return {
            "score_name": rationale.get("score_name", "Attention Score"),
            "market_score": stored_insight.market_score,
            "kol_score": stored_insight.kol_score,
            "smart_money_score": stored_insight.smart_money_score,
            "safety_score": stored_insight.safety_score,
            "final_score": stored_insight.final_score,
            "attention_score": stored_insight.final_score,
            "label": stored_insight.label,
            "summary": stored_insight.summary,
            "generated_at": stored_insight.ts,
            "source_freshness": rationale.get("source_freshness"),
            "rationale": rationale,
        }

    token = db.get(Token, (chain_id, contract_address))
    if token is None:
        return None

    generated = InsightGenerationService(db).generate_token_insight(
        chain_id=chain_id,
        contract_address=contract_address,
        persist=False,
    )
    return {
        "score_name": generated.score_breakdown.score_name,
        "market_score": generated.score_breakdown.market_score,
        "kol_score": generated.score_breakdown.kol_score,
        "smart_money_score": generated.score_breakdown.smart_money_score,
        "safety_score": generated.score_breakdown.safety_score,
        "final_score": generated.score_breakdown.final_score,
        "attention_score": generated.score_breakdown.attention_score,
        "label": generated.score_breakdown.label,
        "summary": generated.summary,
        "generated_at": _now(),
        "source_freshness": generated.rationale.get("source_freshness"),
        "rationale": generated.rationale,
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


def _smart_money_payload(signal: SmartMoneySignal) -> dict[str, Any]:
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


def _kol_detail_mention_payload(
    db: Session,
    mention: TokenMention,
    post: KOLPost,
) -> dict[str, Any]:
    token = None
    chain_name = None
    if mention.is_resolved and mention.chain_id and mention.contract_address:
        token = db.get(Token, (mention.chain_id, mention.contract_address))
        chain_name = build_chain_option(mention.chain_id)["name"]

    return {
        "post_id": mention.post_id,
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


def _latest_signal_time(signals: list[SmartMoneySignal]) -> datetime | None:
    timestamps = [signal.signal_trigger_time or signal.ts for signal in signals if signal.signal_trigger_time or signal.ts]
    return max(timestamps) if timestamps else None


def _latest_kol_post_time_from_mentions(kol_mentions: list[dict[str, Any]]) -> datetime | None:
    timestamps = []
    for mention in kol_mentions:
        created_at = mention.get("created_at")
        if isinstance(created_at, str):
            try:
                timestamps.append(datetime.fromisoformat(created_at.replace("Z", "+00:00")))
            except ValueError:
                continue
    return max(timestamps) if timestamps else None


def _parse_json_text(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _format_token_candidates(items: list[dict[str, Any]]) -> str:
    if not items:
        return "no current matches"

    formatted = [
        f"{item.get('symbol') or item['contract_address']} on {build_chain_option(item['chain_id'])['short_name']} "
        f"(Attention Score {float(item.get('attention_score') or 0.0):.0f})"
        for item in items
    ]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return f"{', '.join(formatted[:-1])}, and {formatted[-1]}"


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now() -> datetime:
    return datetime.now(UTC)
