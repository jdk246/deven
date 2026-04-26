from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
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
from app.services.market_ingestion import build_chain_option, get_enabled_chain_ids
from app.services.scoring import ATTENTION_SCORE_NAME, ScoringService, TokenScoreBreakdown


@dataclass(frozen=True)
class DeterministicInsight:
    chain_id: str
    contract_address: str
    summary: str
    score_breakdown: TokenScoreBreakdown
    rationale: dict[str, Any]


class InsightGenerationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.scoring_service = ScoringService(db)

    def generate_token_insight(
        self,
        *,
        chain_id: str,
        contract_address: str,
        persist: bool = True,
    ) -> DeterministicInsight:
        token = self.db.get(Token, (chain_id, contract_address))
        if token is None:
            raise ValueError(f"Unknown token {chain_id}:{contract_address}")

        breakdown = self.scoring_service.score_token(
            chain_id=chain_id,
            contract_address=contract_address,
            persist=False,
        )
        context = self._load_token_context(
            chain_id=chain_id,
            contract_address=contract_address,
        )
        summary = self._build_summary(token=token, context=context, breakdown=breakdown)
        rationale = self._build_rationale(
            token=token,
            context=context,
            breakdown=breakdown,
            summary=summary,
        )

        insight = DeterministicInsight(
            chain_id=chain_id,
            contract_address=contract_address,
            summary=summary,
            score_breakdown=breakdown,
            rationale=rationale,
        )

        if persist:
            self.store_token_insight(insight)

        return insight

    def generate_all_insights(
        self,
        *,
        chains: list[str] | None = None,
        limit_per_chain: int = 20,
        persist: bool = True,
    ) -> dict[str, Any]:
        clamped_limit = max(1, min(limit_per_chain, 100))
        tracked_tokens = self._tracked_tokens(chains=chains, limit_per_chain=clamped_limit)
        summary: dict[str, Any] = {
            "tokens_seen": len(tracked_tokens),
            "insights_created": 0,
            "errors": [],
        }

        for token in tracked_tokens:
            try:
                self.generate_token_insight(
                    chain_id=token.chain_id,
                    contract_address=token.contract_address,
                    persist=persist,
                )
                if persist:
                    self.db.commit()
                summary["insights_created"] += 1
            except Exception as exc:
                self.db.rollback()
                summary["errors"].append(
                    f"Insight generation failed for {token.chain_id}:{token.contract_address}: {exc}"
                )

        return summary

    def store_token_insight(self, insight: DeterministicInsight) -> TokenInsight:
        stored_insight = TokenInsight(
            chain_id=insight.chain_id,
            contract_address=insight.contract_address,
            market_score=insight.score_breakdown.market_score,
            kol_score=insight.score_breakdown.kol_score,
            smart_money_score=insight.score_breakdown.smart_money_score,
            safety_score=insight.score_breakdown.safety_score,
            final_score=insight.score_breakdown.final_score,
            label=insight.score_breakdown.label,
            summary=insight.summary,
            rationale_json=json.dumps(insight.rationale, default=str, separators=(",", ":")),
        )
        self.db.add(stored_insight)
        return stored_insight

    def _tracked_tokens(
        self,
        *,
        chains: list[str] | None,
        limit_per_chain: int,
    ) -> list[Token]:
        if chains:
            selected_chains = list(dict.fromkeys(chains))
        else:
            selected_chains = get_enabled_chain_ids()

        if selected_chains:
            tokens: list[Token] = []
            for chain_id in selected_chains:
                chain_tokens = self.db.execute(
                    select(Token)
                    .where(Token.chain_id == chain_id)
                    .order_by(desc(Token.updated_at))
                    .limit(limit_per_chain)
                ).scalars().all()
                tokens.extend(chain_tokens)
            return tokens

        return self.db.execute(
            select(Token).order_by(desc(Token.updated_at)).limit(limit_per_chain)
        ).scalars().all()

    def _load_token_context(
        self,
        *,
        chain_id: str,
        contract_address: str,
    ) -> dict[str, Any]:
        snapshot = self.db.execute(
            select(TokenSnapshot)
            .where(
                TokenSnapshot.chain_id == chain_id,
                TokenSnapshot.contract_address == contract_address,
            )
            .order_by(desc(TokenSnapshot.ts))
            .limit(1)
        ).scalar_one_or_none()

        audit = self.db.execute(
            select(TokenAudit)
            .where(
                TokenAudit.chain_id == chain_id,
                TokenAudit.contract_address == contract_address,
            )
            .order_by(desc(TokenAudit.ts))
            .limit(1)
        ).scalar_one_or_none()

        signals = self.db.execute(
            select(SmartMoneySignal)
            .where(
                SmartMoneySignal.chain_id == chain_id,
                SmartMoneySignal.contract_address == contract_address,
            )
            .order_by(desc(SmartMoneySignal.signal_trigger_time), desc(SmartMoneySignal.ts))
            .limit(20)
        ).scalars().all()

        kol_rows = self.db.execute(
            select(KOLPost, KOLProfile, TokenMention)
            .join(TokenMention, TokenMention.post_id == KOLPost.id)
            .join(KOLProfile, KOLPost.kol_id == KOLProfile.id)
            .where(
                TokenMention.chain_id == chain_id,
                TokenMention.contract_address == contract_address,
                TokenMention.is_resolved.is_(True),
            )
            .order_by(desc(KOLPost.created_at), desc(KOLPost.inserted_at))
            .limit(100)
        ).all()

        wallet_positions = self.db.execute(
            select(KOLWalletPosition)
            .where(
                KOLWalletPosition.chain_id == chain_id,
                KOLWalletPosition.contract_address == contract_address,
            )
            .order_by(desc(KOLWalletPosition.ts))
            .limit(50)
        ).scalars().all()

        unique_posts: list[tuple[KOLPost, KOLProfile]] = []
        seen_post_ids: set[int] = set()
        for post, profile, _mention in kol_rows:
            if post.id in seen_post_ids:
                continue
            seen_post_ids.add(post.id)
            unique_posts.append((post, profile))

        return {
            "snapshot": snapshot,
            "audit": audit,
            "signals": signals,
            "kol_posts": unique_posts,
            "wallet_positions": wallet_positions,
        }

    def _build_summary(
        self,
        *,
        token: Token,
        context: dict[str, Any],
        breakdown: TokenScoreBreakdown,
    ) -> str:
        display_label = self._summary_token_label(token)
        market_clause = self._market_clause(context["snapshot"], breakdown.market_score)
        kol_clause = self._kol_clause(context["kol_posts"], breakdown.kol_score)
        smart_money_clause = self._smart_money_clause(
            context["signals"],
            context["snapshot"],
            breakdown.smart_money_score,
        )
        risk_clause = self._risk_clause(
            context["audit"],
            context["snapshot"],
            breakdown.safety_score,
        )

        parts = [
            f"{display_label} falls in the {breakdown.label} range with an {ATTENTION_SCORE_NAME} of {breakdown.final_score:.0f}.",
            market_clause,
            kol_clause,
            smart_money_clause,
            risk_clause,
        ]
        return " ".join(part for part in parts if part)

    def _build_rationale(
        self,
        *,
        token: Token,
        context: dict[str, Any],
        breakdown: TokenScoreBreakdown,
        summary: str,
    ) -> dict[str, Any]:
        market_drivers = self._market_drivers(context["snapshot"])
        kol_drivers = self._kol_drivers(context["kol_posts"])
        smart_money_drivers = self._smart_money_drivers(context["signals"], context["snapshot"])
        risk_warnings = self._risk_warnings(context["audit"], context["snapshot"])
        latest_kol_post = self._latest_kol_post(context["kol_posts"])
        latest_signal_time = self._latest_signal_time(context["signals"])

        return {
            "score_name": ATTENTION_SCORE_NAME,
            "summary_mode": "deterministic",
            "summary": summary,
            "token": {
                "chain_id": token.chain_id,
                "contract_address": token.contract_address,
                "symbol": token.symbol,
                "name": token.name,
                "display_label": self._summary_token_label(token),
            },
            "scores": {
                "market_score": breakdown.market_score,
                "kol_score": breakdown.kol_score,
                "smart_money_score": breakdown.smart_money_score,
                "safety_score": breakdown.safety_score,
                "final_score": breakdown.final_score,
                "label": breakdown.label,
            },
            "key_market_drivers": market_drivers,
            "key_kol_drivers": kol_drivers,
            "smart_money_drivers": smart_money_drivers,
            "risk_warnings": risk_warnings,
            "missing_data": self._missing_data(context),
            "source_freshness": {
                "market_snapshot_at": context["snapshot"].ts.isoformat() if context["snapshot"] else None,
                "audit_at": context["audit"].ts.isoformat() if context["audit"] else None,
                "latest_kol_post_at": latest_kol_post.isoformat() if latest_kol_post else None,
                "latest_smart_money_at": latest_signal_time.isoformat() if latest_signal_time else None,
            },
            "score_rationale": breakdown.rationale,
        }

    def _market_clause(self, snapshot: TokenSnapshot | None, market_score_value: float) -> str:
        if snapshot is None:
            return "Market context is limited because no recent market snapshot is available."

        drivers = self._market_drivers(snapshot)
        if not drivers:
            return f"Market activity is mixed, with a market score of {market_score_value:.0f}."

        return (
            f"Market attention is supported by {', '.join(drivers[:2])}, "
            f"producing a market score of {market_score_value:.0f}."
        )

    def _kol_clause(
        self,
        kol_posts: list[tuple[KOLPost, KOLProfile]],
        kol_score_value: float,
    ) -> str:
        if not kol_posts:
            return "Social coverage is limited because there are no resolved KOL mentions yet."

        sentiments = [self._normalize_key(post.sentiment) for post, _profile in kol_posts]
        bullish = sum(1 for sentiment in sentiments if sentiment == "bullish")
        bearish = sum(1 for sentiment in sentiments if sentiment == "bearish")
        seeded = any(post.source_mode == "seed" for post, _profile in kol_posts)
        sentiment_phrase = "mostly neutral"
        if bullish > bearish and bullish > 0:
            sentiment_phrase = "mostly positive"
        elif bearish > bullish and bearish > 0:
            sentiment_phrase = "skewed cautious"

        source_note = " KOL posts are currently seeded." if seeded else ""
        return (
            f"KOL and social activity shows {len(kol_posts)} mapped mention"
            f"{'' if len(kol_posts) == 1 else 's'} with {sentiment_phrase} tone, "
            f"giving a KOL score of {kol_score_value:.0f}.{source_note}"
        )

    def _smart_money_clause(
        self,
        signals: list[SmartMoneySignal],
        snapshot: TokenSnapshot | None,
        smart_money_score_value: float,
    ) -> str:
        if not signals and snapshot is None:
            return "Smart-money context is limited because no recent signal or holding data is available."

        drivers = self._smart_money_drivers(signals, snapshot)
        if not drivers:
            return f"Smart-money activity is muted, with a smart-money score of {smart_money_score_value:.0f}."

        return (
            f"Smart-money signal reflects {', '.join(drivers[:2])}, "
            f"for a smart-money score of {smart_money_score_value:.0f}."
        )

    def _risk_clause(
        self,
        audit: TokenAudit | None,
        snapshot: TokenSnapshot | None,
        safety_score_value: float,
    ) -> str:
        warnings = self._risk_warnings(audit, snapshot)
        if warnings:
            return (
                f"Risk warnings include {', '.join(warnings[:3])}, "
                f"leaving a safety score of {safety_score_value:.0f}."
            )

        return f"Risk readings are comparatively lighter, with a safety score of {safety_score_value:.0f}."

    def _summary_token_label(self, token: Token) -> str:
        symbol = (token.symbol or "").strip()
        name = (token.name or "").strip()
        if name and symbol and name.casefold() != symbol.casefold():
            base_label = f"{name} ({symbol})"
        else:
            base_label = symbol or name or token.contract_address

        chain_short_name = build_chain_option(token.chain_id)["short_name"]
        return f"{base_label} on {chain_short_name}"

    def _market_drivers(self, snapshot: TokenSnapshot | None) -> list[str]:
        if snapshot is None:
            return []

        drivers: list[str] = []
        if snapshot.volume_24h is not None and snapshot.volume_24h >= 1_000_000.0:
            drivers.append("elevated 24h volume")
        if snapshot.liquidity is not None and snapshot.liquidity >= 250_000.0:
            drivers.append("meaningful liquidity")
        if snapshot.holders is not None and snapshot.holders >= 5_000:
            drivers.append("a broad holder base")
        if snapshot.percent_change_24h is not None and snapshot.percent_change_24h >= 10.0:
            drivers.append("positive 24h momentum")
        elif snapshot.percent_change_24h is not None and snapshot.percent_change_24h <= -10.0:
            drivers.append("negative 24h momentum")
        concentration_pct = self._percent(snapshot.top10_holders_pct)
        if concentration_pct is not None and concentration_pct <= 50.0:
            drivers.append("moderate holder concentration")
        return drivers

    def _kol_drivers(self, kol_posts: list[tuple[KOLPost, KOLProfile]]) -> list[str]:
        if not kol_posts:
            return []

        drivers: list[str] = [f"{len(kol_posts)} resolved KOL mention{'s' if len(kol_posts) != 1 else ''}"]
        total_likes = sum(post.like_count or 0 for post, _profile in kol_posts)
        total_reposts = sum(post.repost_count or 0 for post, _profile in kol_posts)
        bullish = sum(1 for post, _profile in kol_posts if self._normalize_key(post.sentiment) == "bullish")
        bearish = sum(1 for post, _profile in kol_posts if self._normalize_key(post.sentiment) == "bearish")

        if bullish > bearish and bullish > 0:
            drivers.append("net positive KOL tone")
        elif bearish > bullish and bearish > 0:
            drivers.append("some bearish KOL tone")

        if total_likes + (2 * total_reposts) >= 500:
            drivers.append("healthy engagement across recent posts")

        if any(post.source_mode == "seed" for post, _profile in kol_posts):
            drivers.append("seeded KOL dataset")

        return drivers

    def _smart_money_drivers(
        self,
        signals: list[SmartMoneySignal],
        snapshot: TokenSnapshot | None,
    ) -> list[str]:
        drivers: list[str] = []
        if signals:
            positive_signals = sum(
                1
                for signal in signals
                if self._normalize_key(signal.direction) in {"buy", "long", "accumulate", "bullish"}
            )
            negative_signals = sum(
                1
                for signal in signals
                if self._normalize_key(signal.direction) in {"sell", "short", "bearish", "exit"}
            )
            if positive_signals > negative_signals and positive_signals > 0:
                drivers.append(f"{positive_signals} recent positive smart-money signal{'s' if positive_signals != 1 else ''}")
            elif negative_signals > positive_signals and negative_signals > 0:
                drivers.append(f"{negative_signals} recent negative smart-money signal{'s' if negative_signals != 1 else ''}")

            active_count = sum(
                1
                for signal in signals
                if self._normalize_key(signal.status) in {"active", "open", "running"}
            )
            if active_count > 0:
                drivers.append(f"{active_count} active smart-money setup{'s' if active_count != 1 else ''}")

        if snapshot and snapshot.smart_money_holding_pct is not None:
            holding_pct = self._percent(snapshot.smart_money_holding_pct)
            if holding_pct is not None and holding_pct >= 5.0:
                drivers.append(f"smart-money holding is around {holding_pct:.1f}%")

        return drivers

    def _risk_warnings(
        self,
        audit: TokenAudit | None,
        snapshot: TokenSnapshot | None,
    ) -> list[str]:
        warnings: list[str] = []
        if audit is None or audit.has_result is False:
            warnings.append("audit coverage is unavailable")
        else:
            risk_level = self._normalize_key(audit.risk_level_enum)
            if risk_level == "high":
                warnings.append("high audit risk")
            elif risk_level == "medium":
                warnings.append("medium audit risk")

            if audit.is_verified is False:
                warnings.append("contract verification is missing")

            buy_tax_pct = self._percent(audit.buy_tax)
            if buy_tax_pct is not None and buy_tax_pct > 5.0:
                warnings.append(f"buy tax is elevated at {buy_tax_pct:.1f}%")

            sell_tax_pct = self._percent(audit.sell_tax)
            if sell_tax_pct is not None and sell_tax_pct > 5.0:
                warnings.append(f"sell tax is elevated at {sell_tax_pct:.1f}%")

        if snapshot is not None:
            concentration_pct = self._percent(snapshot.top10_holders_pct)
            if concentration_pct is not None and concentration_pct > 80.0:
                warnings.append("holder concentration is very high")
            elif concentration_pct is not None and concentration_pct > 60.0:
                warnings.append("holder concentration is elevated")

            if snapshot.liquidity is not None and snapshot.liquidity < 100_000.0:
                warnings.append("liquidity is on the lighter side")

        return warnings

    def _missing_data(self, context: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        if context["snapshot"] is None:
            missing.append("market_snapshot")
        if context["audit"] is None:
            missing.append("audit_data")
        if not context["signals"]:
            missing.append("smart_money_signals")
        if not context["kol_posts"]:
            missing.append("kol_mentions")
        return missing

    def _latest_kol_post(self, kol_posts: list[tuple[KOLPost, KOLProfile]]) -> datetime | None:
        timestamps = [
            self._to_utc(post.created_at or post.inserted_at)
            for post, _profile in kol_posts
            if post.created_at or post.inserted_at
        ]
        return max(timestamps) if timestamps else None

    def _latest_signal_time(self, signals: list[SmartMoneySignal]) -> datetime | None:
        timestamps = [
            self._to_utc(signal.signal_trigger_time or signal.ts)
            for signal in signals
            if signal.signal_trigger_time or signal.ts
        ]
        return max(timestamps) if timestamps else None

    def _normalize_key(self, value: str | None) -> str:
        if value is None:
            return ""
        return value.strip().lower()

    def _percent(self, value: float | None) -> float | None:
        if value is None:
            return None
        numeric = float(value)
        if 0.0 <= abs(numeric) <= 1.0:
            return numeric * 100.0
        return numeric

    def _to_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
