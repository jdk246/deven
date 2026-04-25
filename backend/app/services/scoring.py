from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    KOLPost,
    KOLProfile,
    KOLWalletPosition,
    SmartMoneySignal,
    Token,
    TokenAudit,
    TokenInsight,
    TokenMention,
    TokenSnapshot,
)

ATTENTION_SCORE_NAME = "Attention Score"

SENTIMENT_WEIGHTS = {
    "bullish": 1.0,
    "neutral": 0.2,
    "bearish": -1.0,
    "unknown": 0.0,
}

DIRECTION_WEIGHTS = {
    "buy": 1.0,
    "long": 1.0,
    "accumulate": 0.8,
    "bullish": 0.8,
    "sell": -1.0,
    "short": -1.0,
    "bearish": -0.8,
    "exit": -0.8,
}

STATUS_SCORES = {
    "active": 100.0,
    "open": 100.0,
    "running": 95.0,
    "completed": 70.0,
    "closed": 55.0,
    "timeout": 40.0,
    "timed_out": 40.0,
    "expired": 35.0,
    "inactive": 45.0,
}

STATUS_IMPORTANCE = {
    "active": 1.0,
    "open": 1.0,
    "running": 1.0,
    "completed": 0.7,
    "closed": 0.55,
    "timeout": 0.45,
    "timed_out": 0.45,
    "expired": 0.35,
    "inactive": 0.4,
}


@dataclass(frozen=True)
class KOLScoreInput:
    created_at: datetime | None
    sentiment: str | None
    like_count: int | None
    repost_count: int | None
    reply_count: int | None
    view_count: int | None
    priority: int | None


@dataclass(frozen=True)
class SmartMoneyScoreInput:
    direction: str | None
    smart_money_count: int | None
    status: str | None
    total_token_value: float | None
    max_gain: float | None
    exit_rate: float | None
    signal_trigger_time: datetime | None


@dataclass(frozen=True)
class TokenScoreBreakdown:
    chain_id: str
    contract_address: str
    score_name: str
    market_score: float
    kol_score: float
    smart_money_score: float
    safety_score: float
    final_score: float
    attention_score: float
    label: str
    rationale: dict[str, Any]


def market_score(
    *,
    volume_24h: float | None,
    liquidity: float | None,
    holders: int | None,
    percent_change_1h: float | None,
    percent_change_24h: float | None,
    top10_holders_pct: float | None,
) -> float:
    components = [
        (_log_scale(volume_24h, 50_000.0, 10_000_000.0), 25.0, volume_24h is not None),
        (_log_scale(liquidity, 25_000.0, 5_000_000.0), 20.0, liquidity is not None),
        (_log_scale(holders, 100.0, 50_000.0), 15.0, holders is not None),
        (_momentum_score(percent_change_1h, downside=-15.0, upside=15.0), 15.0, percent_change_1h is not None),
        (_momentum_score(percent_change_24h, downside=-30.0, upside=40.0), 15.0, percent_change_24h is not None),
        (_concentration_quality(top10_holders_pct), 10.0, top10_holders_pct is not None),
    ]
    return _weighted_score(components, apply_coverage_penalty=True)


def kol_score(
    *,
    mentions: list[KOLScoreInput],
    wallet_evidence_count: int = 0,
    now: datetime | None = None,
) -> float:
    if not mentions:
        return 0.0

    effective_now = now or _now()
    weights: list[float] = []
    engagement_values: list[float] = []
    recency_values: list[float] = []
    sentiment_values: list[float] = []

    for mention in mentions:
        priority_weight = _priority_weight(mention.priority)
        recency_decay = _recency_decay(mention.created_at, effective_now)
        weight = priority_weight * max(recency_decay, 0.05)
        weights.append(weight)
        recency_values.append(recency_decay)
        sentiment_values.append(SENTIMENT_WEIGHTS.get((mention.sentiment or "unknown").lower(), 0.0))
        engagement_values.append(_engagement_value(mention))

    mention_count_component = _log_scale(float(len(mentions)), 1.0, 20.0) or 0.0
    engagement_component = _linear_scale(_weighted_average(engagement_values, weights), 0.5, 8.5) or 0.0
    recency_component = _clamp(_weighted_average(recency_values, weights) * 100.0)
    sentiment_component = _clamp(50.0 + 50.0 * _weighted_average(sentiment_values, weights))
    wallet_component = _log_scale(float(wallet_evidence_count), 1.0, 5.0) or 0.0

    return _clamp(
        0.30 * mention_count_component
        + 0.25 * sentiment_component
        + 0.20 * engagement_component
        + 0.15 * recency_component
        + 0.10 * wallet_component
    )


def smart_money_score(
    *,
    signals: list[SmartMoneyScoreInput],
    smart_money_holding_pct: float | None,
    now: datetime | None = None,
) -> float:
    effective_now = now or _now()
    if not signals and smart_money_holding_pct is None:
        return 0.0

    direction_values: list[float] = []
    status_values: list[float] = []
    status_weights: list[float] = []
    count_total = 0.0
    max_total_token_value: float | None = None
    max_gain_value: float | None = None
    exit_values: list[float] = []
    exit_weights: list[float] = []

    for signal in signals:
        status_key = _normalize_key(signal.status)
        direction_key = _normalize_key(signal.direction)
        importance = STATUS_IMPORTANCE.get(status_key, 0.6)
        smart_money_count = float(max(signal.smart_money_count or 0, 1))
        recency = _signal_recency_weight(signal.signal_trigger_time, effective_now)
        weight = importance * smart_money_count * recency

        direction_values.append(DIRECTION_WEIGHTS.get(direction_key, 0.0))
        status_values.append(STATUS_SCORES.get(status_key, 50.0))
        status_weights.append(weight)
        count_total += smart_money_count * importance

        if signal.total_token_value is not None:
            max_total_token_value = max(max_total_token_value or 0.0, float(signal.total_token_value))

        if signal.max_gain is not None:
            max_gain_value = max(max_gain_value or float("-inf"), float(signal.max_gain))

        exit_rate_pct = _rate_to_percent(signal.exit_rate)
        if exit_rate_pct is not None:
            exit_values.append(100.0 - (_linear_scale(exit_rate_pct, 10.0, 80.0) or 0.0))
            exit_weights.append(weight)

    components = [
        (
            _clamp(50.0 + 50.0 * _weighted_average(direction_values, status_weights)),
            25.0,
            bool(direction_values),
        ),
        (_log_scale(count_total, 1.0, 25.0), 20.0, count_total > 0.0),
        (_weighted_average(status_values, status_weights), 15.0, bool(status_values)),
        (_log_scale(max_total_token_value, 5_000.0, 500_000.0), 15.0, max_total_token_value is not None),
        (_linear_scale(_rate_to_percent(smart_money_holding_pct), 0.0, 15.0), 15.0, smart_money_holding_pct is not None),
        (_linear_scale(max_gain_value, 0.0, 100.0), 5.0, max_gain_value is not None),
        (_weighted_average(exit_values, exit_weights), 5.0, bool(exit_values)),
    ]
    return _weighted_score(components, apply_coverage_penalty=False)


def safety_score(
    *,
    risk_level_enum: str | None,
    risk_level: int | None,
    buy_tax: float | None,
    sell_tax: float | None,
    is_verified: bool | None,
    top10_holders_pct: float | None,
    liquidity: float | None,
    audit_available: bool,
) -> float:
    score = 100.0

    if not audit_available:
        score -= 25.0
    else:
        risk_key = _normalize_key(risk_level_enum)
        if risk_key == "high":
            score -= 75.0
        elif risk_key == "medium":
            score -= 35.0
        elif risk_key not in {"low", ""} and risk_level is not None:
            if risk_level >= 70:
                score -= 75.0
            elif risk_level >= 40:
                score -= 35.0

        if is_verified is False:
            score -= 15.0

        buy_tax_pct = _rate_to_percent(buy_tax)
        if buy_tax_pct is not None and buy_tax_pct > 5.0:
            score -= 15.0

        sell_tax_pct = _rate_to_percent(sell_tax)
        if sell_tax_pct is not None and sell_tax_pct > 5.0:
            score -= 20.0

    concentration_pct = _rate_to_percent(top10_holders_pct)
    if concentration_pct is not None:
        if concentration_pct > 80.0:
            score -= 20.0
        elif concentration_pct > 60.0:
            score -= 10.0

    if liquidity is not None:
        if liquidity < 25_000.0:
            score -= 20.0
        elif liquidity < 100_000.0:
            score -= 10.0

    return _clamp(score)


def final_score(
    *,
    market_score_value: float,
    kol_score_value: float,
    smart_money_score_value: float,
    safety_score_value: float,
) -> float:
    return _clamp(
        0.35 * market_score_value
        + 0.25 * kol_score_value
        + 0.25 * smart_money_score_value
        + 0.15 * safety_score_value
    )


def attention_label(score: float) -> str:
    if score >= 80.0:
        return "High Attention"
    if score >= 60.0:
        return "Watchlist"
    if score >= 40.0:
        return "Mixed Signal"
    return "Weak / Risky"


class ScoringService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def score_token(
        self,
        *,
        chain_id: str,
        contract_address: str,
        persist: bool = False,
    ) -> TokenScoreBreakdown:
        token = self.db.get(Token, (chain_id, contract_address))
        if token is None:
            raise ValueError(f"Unknown token {chain_id}:{contract_address}")

        snapshot = self._latest_snapshot(chain_id=chain_id, contract_address=contract_address)
        audit = self._latest_audit(chain_id=chain_id, contract_address=contract_address)
        smart_money_inputs = self._smart_money_inputs(chain_id=chain_id, contract_address=contract_address)
        kol_inputs = self._kol_inputs(chain_id=chain_id, contract_address=contract_address)
        wallet_evidence_count = self._wallet_evidence_count(
            chain_id=chain_id,
            contract_address=contract_address,
        )

        market_value = market_score(
            volume_24h=snapshot.volume_24h if snapshot else None,
            liquidity=snapshot.liquidity if snapshot else None,
            holders=snapshot.holders if snapshot else None,
            percent_change_1h=snapshot.percent_change_1h if snapshot else None,
            percent_change_24h=snapshot.percent_change_24h if snapshot else None,
            top10_holders_pct=snapshot.top10_holders_pct if snapshot else None,
        )
        kol_value = kol_score(
            mentions=kol_inputs,
            wallet_evidence_count=wallet_evidence_count,
        )
        smart_money_value = smart_money_score(
            signals=smart_money_inputs,
            smart_money_holding_pct=snapshot.smart_money_holding_pct if snapshot else None,
        )
        safety_value = safety_score(
            risk_level_enum=audit.risk_level_enum if audit else None,
            risk_level=audit.risk_level if audit else None,
            buy_tax=audit.buy_tax if audit else None,
            sell_tax=audit.sell_tax if audit else None,
            is_verified=audit.is_verified if audit else None,
            top10_holders_pct=snapshot.top10_holders_pct if snapshot else None,
            liquidity=snapshot.liquidity if snapshot else None,
            audit_available=bool(audit and (audit.has_result is not False)),
        )
        attention_value = final_score(
            market_score_value=market_value,
            kol_score_value=kol_value,
            smart_money_score_value=smart_money_value,
            safety_score_value=safety_value,
        )
        label = attention_label(attention_value)

        rationale = {
            "score_name": ATTENTION_SCORE_NAME,
            "token": {
                "chain_id": chain_id,
                "contract_address": contract_address,
                "symbol": token.symbol,
                "name": token.name,
            },
            "components": {
                "market_score": market_value,
                "kol_score": kol_value,
                "smart_money_score": smart_money_value,
                "safety_score": safety_value,
                "final_score": attention_value,
            },
            "inputs": {
                "snapshot": {
                    "volume_24h": snapshot.volume_24h if snapshot else None,
                    "liquidity": snapshot.liquidity if snapshot else None,
                    "holders": snapshot.holders if snapshot else None,
                    "percent_change_1h": snapshot.percent_change_1h if snapshot else None,
                    "percent_change_24h": snapshot.percent_change_24h if snapshot else None,
                    "top10_holders_pct": snapshot.top10_holders_pct if snapshot else None,
                    "smart_money_holding_pct": snapshot.smart_money_holding_pct if snapshot else None,
                },
                "audit": {
                    "risk_level_enum": audit.risk_level_enum if audit else None,
                    "risk_level": audit.risk_level if audit else None,
                    "buy_tax": audit.buy_tax if audit else None,
                    "sell_tax": audit.sell_tax if audit else None,
                    "is_verified": audit.is_verified if audit else None,
                    "available": bool(audit and (audit.has_result is not False)),
                },
                "kol_mentions": len(kol_inputs),
                "wallet_evidence_count": wallet_evidence_count,
                "smart_money_signals": len(smart_money_inputs),
            },
        }

        breakdown = TokenScoreBreakdown(
            chain_id=chain_id,
            contract_address=contract_address,
            score_name=ATTENTION_SCORE_NAME,
            market_score=round(market_value, 2),
            kol_score=round(kol_value, 2),
            smart_money_score=round(smart_money_value, 2),
            safety_score=round(safety_value, 2),
            final_score=round(attention_value, 2),
            attention_score=round(attention_value, 2),
            label=label,
            rationale=rationale,
        )

        if persist:
            self.store_token_score(breakdown)

        return breakdown

    def store_token_score(self, breakdown: TokenScoreBreakdown) -> TokenInsight:
        insight = TokenInsight(
            chain_id=breakdown.chain_id,
            contract_address=breakdown.contract_address,
            market_score=breakdown.market_score,
            kol_score=breakdown.kol_score,
            smart_money_score=breakdown.smart_money_score,
            safety_score=breakdown.safety_score,
            final_score=breakdown.final_score,
            label=breakdown.label,
            summary=f"{ATTENTION_SCORE_NAME}: {breakdown.label}",
            rationale_json=json.dumps(breakdown.rationale, default=str, separators=(",", ":")),
        )
        self.db.add(insight)
        return insight

    def _latest_snapshot(self, *, chain_id: str, contract_address: str) -> TokenSnapshot | None:
        return self.db.execute(
            select(TokenSnapshot)
            .where(
                TokenSnapshot.chain_id == chain_id,
                TokenSnapshot.contract_address == contract_address,
            )
            .order_by(desc(TokenSnapshot.ts))
            .limit(1)
        ).scalar_one_or_none()

    def _latest_audit(self, *, chain_id: str, contract_address: str) -> TokenAudit | None:
        return self.db.execute(
            select(TokenAudit)
            .where(
                TokenAudit.chain_id == chain_id,
                TokenAudit.contract_address == contract_address,
            )
            .order_by(desc(TokenAudit.ts))
            .limit(1)
        ).scalar_one_or_none()

    def _smart_money_inputs(
        self,
        *,
        chain_id: str,
        contract_address: str,
        limit: int = 20,
    ) -> list[SmartMoneyScoreInput]:
        signals = self.db.execute(
            select(SmartMoneySignal)
            .where(
                SmartMoneySignal.chain_id == chain_id,
                SmartMoneySignal.contract_address == contract_address,
            )
            .order_by(desc(SmartMoneySignal.signal_trigger_time), desc(SmartMoneySignal.ts))
            .limit(limit)
        ).scalars().all()

        return [
            SmartMoneyScoreInput(
                direction=signal.direction,
                smart_money_count=signal.smart_money_count,
                status=signal.status,
                total_token_value=signal.total_token_value,
                max_gain=signal.max_gain,
                exit_rate=signal.exit_rate,
                signal_trigger_time=signal.signal_trigger_time or signal.ts,
            )
            for signal in signals
        ]

    def _kol_inputs(
        self,
        *,
        chain_id: str,
        contract_address: str,
        limit: int = 100,
    ) -> list[KOLScoreInput]:
        rows = self.db.execute(
            select(KOLPost, KOLProfile)
            .join(TokenMention, TokenMention.post_id == KOLPost.id)
            .join(KOLProfile, KOLPost.kol_id == KOLProfile.id)
            .where(
                TokenMention.chain_id == chain_id,
                TokenMention.contract_address == contract_address,
                TokenMention.is_resolved.is_(True),
            )
            .order_by(desc(KOLPost.created_at), desc(KOLPost.inserted_at))
            .limit(limit)
        ).all()

        unique_posts: dict[int, KOLScoreInput] = {}
        for post, profile in rows:
            if post.id in unique_posts:
                continue
            unique_posts[post.id] = KOLScoreInput(
                created_at=post.created_at or post.inserted_at,
                sentiment=post.sentiment,
                like_count=post.like_count,
                repost_count=post.repost_count,
                reply_count=post.reply_count,
                view_count=post.view_count,
                priority=profile.priority,
            )

        return list(unique_posts.values())

    def _wallet_evidence_count(
        self,
        *,
        chain_id: str,
        contract_address: str,
    ) -> int:
        return int(
            self.db.execute(
                select(func.count(distinct(KOLWalletPosition.kol_wallet_id))).where(
                    KOLWalletPosition.chain_id == chain_id,
                    KOLWalletPosition.contract_address == contract_address,
                )
            ).scalar_one()
            or 0
        )


def _weighted_score(
    components: list[tuple[float | None, float, bool]],
    *,
    apply_coverage_penalty: bool,
) -> float:
    present_components = [
        (score, weight)
        for score, weight, is_present in components
        if is_present and score is not None
    ]
    if not present_components:
        return 0.0

    raw_score = _weighted_average(
        [score for score, _ in present_components],
        [weight for _, weight in present_components],
    )
    if not apply_coverage_penalty:
        return _clamp(raw_score)

    total_weight = sum(weight for _, weight, _ in components)
    present_weight = sum(weight for _, weight in present_components)
    coverage_ratio = present_weight / total_weight if total_weight else 0.0
    return _clamp(raw_score * (0.65 + 0.35 * coverage_ratio))


def _weighted_average(values: list[float], weights: list[float]) -> float:
    if not values or not weights or len(values) != len(weights):
        return 0.0
    total_weight = sum(weights)
    if total_weight <= 0.0:
        return 0.0
    return sum(value * weight for value, weight in zip(values, weights, strict=True)) / total_weight


def _log_scale(value: float | int | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric <= 0.0:
        return 0.0
    if low <= 0.0 or high <= low:
        return None
    scaled = (math.log(numeric) - math.log(low)) / (math.log(high) - math.log(low))
    return _clamp(scaled * 100.0)


def _linear_scale(value: float | None, low: float, high: float) -> float | None:
    if value is None or high <= low:
        return None
    numeric = float(value)
    if numeric <= low:
        return 0.0
    if numeric >= high:
        return 100.0
    return ((numeric - low) / (high - low)) * 100.0


def _momentum_score(value: float | None, *, downside: float, upside: float) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric >= 0.0:
        return _clamp(50.0 + 50.0 * min(numeric, upside) / upside) if upside > 0.0 else 50.0
    return _clamp(50.0 + 50.0 * max(numeric, downside) / abs(downside)) if downside < 0.0 else 50.0


def _concentration_quality(value: float | None) -> float | None:
    concentration_pct = _rate_to_percent(value)
    if concentration_pct is None:
        return None
    if concentration_pct <= 20.0:
        return 100.0
    if concentration_pct <= 40.0:
        return 100.0 - ((concentration_pct - 20.0) / 20.0) * 20.0
    if concentration_pct <= 60.0:
        return 80.0 - ((concentration_pct - 40.0) / 20.0) * 20.0
    if concentration_pct <= 80.0:
        return 60.0 - ((concentration_pct - 60.0) / 20.0) * 35.0
    if concentration_pct <= 95.0:
        return 25.0 - ((concentration_pct - 80.0) / 15.0) * 25.0
    return 0.0


def _engagement_value(mention: KOLScoreInput) -> float:
    total = (
        float(mention.like_count or 0)
        + 2.0 * float(mention.repost_count or 0)
        + float(mention.reply_count or 0)
        + 0.01 * float(mention.view_count or 0)
    )
    return math.log1p(max(total, 0.0))


def _priority_weight(priority: int | None) -> float:
    if priority is None or priority <= 0:
        return 0.6
    return max(0.2, 1.0 / math.sqrt(float(priority)))


def _recency_decay(value: datetime | None, now: datetime) -> float:
    if value is None:
        return 0.2
    created_at = _to_utc(value)
    hours_since = max((now - created_at).total_seconds() / 3600.0, 0.0)
    return math.exp(-hours_since / 36.0)


def _signal_recency_weight(value: datetime | None, now: datetime) -> float:
    if value is None:
        return 0.5
    signal_time = _to_utc(value)
    hours_since = max((now - signal_time).total_seconds() / 3600.0, 0.0)
    return max(0.35, math.exp(-hours_since / 72.0))


def _rate_to_percent(value: float | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if 0.0 <= abs(numeric) <= 1.0:
        return numeric * 100.0
    return numeric


def _normalize_key(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _now() -> datetime:
    return datetime.now(UTC)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))
