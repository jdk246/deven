from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    KOLCall,
    KOLCallPriceObservation,
    KOLPost,
    KOLProfile,
    KOLTrackRecordScore,
    Token,
    TokenMention,
    TokenSnapshot,
)
from app.services.market_ingestion import build_chain_option

TRACK_RECORD_WINDOW = "24h"
TRACK_RECORD_METHODOLOGY = (
    "KOL rankings are based on post-event token movement after tracked KOL mentions. "
    "They are correlation-based, sample-size adjusted, and not financial advice."
)
TRACK_RECORD_DISCLAIMER = "This is correlation-based market research only and not financial advice."

ALLOWED_DIRECTIONS = {"bullish", "bearish", "neutral", "unknown"}
EVALUATED_STATUS = "evaluated"
PENDING_STATUS = "pending"
INSUFFICIENT_STATUS = "insufficient_price_data"
UNRESOLVED_STATUS = "unresolved_token"
SKIPPED_NEUTRAL_STATUS = "skipped_neutral"
ERROR_STATUS = "error"

WINDOW_DELTAS: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}
WINDOW_TOLERANCES: dict[str, timedelta] = {
    "post": timedelta(hours=6),
    "1h": timedelta(hours=2),
    "6h": timedelta(hours=8),
    "24h": timedelta(hours=18),
    "7d": timedelta(days=2),
}
DERIVABLE_PERCENT_FIELDS = {
    "1h": "percent_change_1h",
    "24h": "percent_change_24h",
}

DEMO_KOL_HANDLE_ALIASES = {
    "macro_mina": "raoul_pal_demo",
    "raoul_pal": "raoul_pal_demo",
    "raoul_pal_demo": "raoul_pal_demo",
    "onchain_omar": "willy_woo_demo",
    "willy_woo": "willy_woo_demo",
    "willy_woo_demo": "willy_woo_demo",
    "sol_sage": "ansem_demo",
    "ansem": "ansem_demo",
    "ansem_demo": "ansem_demo",
    "bsc_bella": "crypto_kaleo_demo",
    "crypto_kaleo": "crypto_kaleo_demo",
    "crypto_kaleo_demo": "crypto_kaleo_demo",
    "base_beacon": "cobie_demo",
    "cobie": "cobie_demo",
    "cobie_demo": "cobie_demo",
    "meme_marshal": "murad_demo",
    "murad": "murad_demo",
    "murad_demo": "murad_demo",
    "defi_dahlia": "michael_vandepoppe_demo",
    "michael_vandepoppe": "michael_vandepoppe_demo",
    "michael_vandepoppe_demo": "michael_vandepoppe_demo",
    "ai_arden": "alex_becker_demo",
    "alex_becker": "alex_becker_demo",
    "alex_becker_demo": "alex_becker_demo",
    "wallet_wren": "loomdart_demo",
    "loomdart": "loomdart_demo",
    "loomdart_demo": "loomdart_demo",
    "liquidity_luca": "daan_crypto_demo",
    "daan_crypto": "daan_crypto_demo",
    "daan_crypto_demo": "daan_crypto_demo",
    "builder_brynn": "mert_demo",
    "mert": "mert_demo",
    "mert_demo": "mert_demo",
    "risk_rhea": "zachxbt_demo",
    "zachxbt": "zachxbt_demo",
    "zachxbt_demo": "zachxbt_demo",
    "narrative_niko": "pentoshi_demo",
    "pentoshi": "pentoshi_demo",
    "pentoshi_demo": "pentoshi_demo",
    "flow_faiza": "arthur_hayes_demo",
    "arthur_hayes": "arthur_hayes_demo",
    "arthur_hayes_demo": "arthur_hayes_demo",
    "token_tori": "altcoin_sherpa_demo",
    "altcoin_sherpa": "altcoin_sherpa_demo",
    "altcoin_sherpa_demo": "altcoin_sherpa_demo",
    "chain_chase": "miles_deutscher_demo",
    "miles_deutscher": "miles_deutscher_demo",
    "miles_deutscher_demo": "miles_deutscher_demo",
    "yield_yara": "crypto_cred_demo",
    "crypto_cred": "crypto_cred_demo",
    "crypto_cred_demo": "crypto_cred_demo",
    "alpha_avery": "emperorbtc_demo",
    "emperorbtc": "emperorbtc_demo",
    "emperorbtc_demo": "emperorbtc_demo",
    "chart_cedric": "credibull_demo",
    "credibull": "credibull_demo",
    "credibull_demo": "credibull_demo",
    "dune_dara": "ki_young_ju_demo",
    "ki_young_ju": "ki_young_ju_demo",
    "ki_young_ju_demo": "ki_young_ju_demo",
}

DEMO_KOL_ALIGNMENT_GROUPS = {
    "raoul_pal_demo": "strong",
    "willy_woo_demo": "strong",
    "ansem_demo": "positive",
    "crypto_kaleo_demo": "positive",
    "cobie_demo": "positive",
    "murad_demo": "mixed",
    "michael_vandepoppe_demo": "positive",
    "alex_becker_demo": "mixed",
    "loomdart_demo": "positive",
    "daan_crypto_demo": "mixed",
    "mert_demo": "mixed",
    "zachxbt_demo": "positive",
    "pentoshi_demo": "positive",
    "arthur_hayes_demo": "mixed",
    "altcoin_sherpa_demo": "mixed",
    "miles_deutscher_demo": "positive",
    "crypto_cred_demo": "mixed",
    "emperorbtc_demo": "mixed",
    "credibull_demo": "weak",
    "ki_young_ju_demo": "strong",
}

DEMO_ALIGNMENT_PATTERNS: dict[str, list[bool]] = {
    "strong": [True, True, True, False, True, True],
    "positive": [True, True, False, True, False, True],
    "mixed": [True, False, True, False, True, False],
    "weak": [False, True, False, False, True, False],
}

DEMO_ALIGNMENT_MAGNITUDES: dict[str, list[float]] = {
    "strong": [0.062, 0.044, 0.031, 0.025, 0.053, 0.038],
    "positive": [0.051, 0.034, 0.028, 0.041, 0.023, 0.036],
    "mixed": [0.037, 0.026, 0.021, 0.029, 0.018, 0.024],
    "weak": [0.031, 0.021, 0.027, 0.034, 0.019, 0.022],
}

DEMO_CATEGORY_SYMBOLS: dict[str, list[str]] = {
    "macro": ["BTC", "ETH", "BNB", "SOL", "AAVE"],
    "onchain": ["BTC", "ETH", "BNB", "SOL", "LINK"],
    "solana": ["SOL", "BONK", "WIF", "JUP", "PYTH"],
    "bsc": ["BNB", "CAKE", "BAKE", "XVS", "LISTA"],
    "base": ["BRETT", "AERO", "DEGEN", "TOSHI", "KEYCAT"],
    "memecoin": ["PEPE", "WIF", "BONK", "FLOKI", "DOGE"],
    "defi": ["AAVE", "UNI", "MKR", "LDO", "ENA"],
    "ai": ["FET", "TAO", "RENDER", "VIRTUAL", "WLD"],
    "smart_money": ["BTC", "ETH", "BNB", "SOL", "AERO"],
    "market_structure": ["BTC", "ETH", "BNB", "SOL", "AAVE"],
    "builders": ["SOL", "ETH", "BNB", "PYTH", "JUP"],
    "security": ["BTC", "ETH", "BNB", "SOL", "LINK"],
    "narratives": ["WIF", "PEPE", "BRETT", "BONK", "FET"],
    "trader": ["SOL", "ETH", "BTC", "WIF", "BONK"],
    "multi_chain": ["BTC", "ETH", "BNB", "SOL", "AERO"],
    "research": ["BTC", "ETH", "SOL", "AAVE", "FET"],
    "technical": ["BTC", "ETH", "SOL", "BNB", "WIF"],
    "analytics": ["BTC", "ETH", "BNB", "SOL", "LINK"],
}


@dataclass(frozen=True)
class PricePoint:
    price: float | None
    source: str | None
    observed_at: datetime | None
    detail: dict[str, Any]


class KOLPerformanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_kol_calls_from_mentions(self) -> dict[str, Any]:
        rows = self.db.execute(
            select(TokenMention, KOLPost)
            .join(KOLPost, TokenMention.post_id == KOLPost.id)
            .where(
                TokenMention.is_resolved.is_(True),
                TokenMention.chain_id.is_not(None),
                TokenMention.contract_address.is_not(None),
            )
            .order_by(asc(TokenMention.id))
        ).all()

        calls_created = 0
        warnings: list[str] = []

        for mention, post in rows:
            existing = self.db.execute(
                select(KOLCall).where(
                    KOLCall.post_id == post.id,
                    KOLCall.chain_id == mention.chain_id,
                    KOLCall.contract_address == mention.contract_address,
                )
            ).scalar_one_or_none()

            direction = self._normalize_direction(mention.sentiment or post.sentiment)
            confidence = self._combined_confidence(
                mention.confidence,
                post.sentiment_score,
                direction=direction,
            )
            raw_mention_payload = {
                "mention_id": mention.id,
                "post_id": post.id,
                "mention_type": mention.mention_type,
                "symbol_text": mention.symbol_text,
                "mention_sentiment": mention.sentiment,
                "post_sentiment": post.sentiment,
                "mention_confidence": mention.confidence,
                "post_sentiment_score": post.sentiment_score,
            }

            call = existing or KOLCall(
                kol_id=post.kol_id,
                post_id=post.id,
                chain_id=str(mention.chain_id),
                contract_address=str(mention.contract_address),
                post_created_at=self._call_timestamp(post),
                source_mode=post.source_mode,
                direction=direction,
            )
            call.kol_id = post.kol_id
            call.post_id = post.id
            call.chain_id = str(mention.chain_id)
            call.contract_address = str(mention.contract_address)
            call.symbol_text = mention.symbol_text
            call.direction = direction
            call.confidence = confidence
            call.post_created_at = self._call_timestamp(post)
            call.source_mode = post.source_mode
            call.raw_mention_json = self._json_text(raw_mention_payload)
            self.db.add(call)

            if existing is None:
                calls_created += 1

        self.db.flush()
        calls_created += self._create_seed_demo_calls()

        self._commit_or_rollback(warnings, "Failed to create KOL calls from mentions.")
        return {
            "calls_created": calls_created,
            "warnings": warnings,
        }

    def _create_seed_demo_calls(self) -> int:
        rows = self.db.execute(
            select(KOLPost, KOLProfile)
            .join(KOLProfile, KOLPost.kol_id == KOLProfile.id)
            .where(KOLPost.source_mode == "seed")
            .order_by(asc(KOLPost.created_at), asc(KOLPost.id))
        ).all()

        calls_created = 0
        for post, profile in rows:
            normalized_handle = self._normalize_handle(profile.handle)
            if normalized_handle not in DEMO_KOL_ALIGNMENT_GROUPS:
                continue

            existing_calls = self.db.execute(
                select(KOLCall).where(KOLCall.post_id == post.id)
            ).scalars().all()
            existing_symbols = {
                (call.symbol_text or "").strip().upper()
                for call in existing_calls
                if (call.symbol_text or "").strip()
            }

            direction = self._seed_demo_direction(
                post.sentiment,
                text=post.text,
                priority=profile.priority,
            )
            confidence = self._combined_confidence(
                mention_confidence=None,
                sentiment_score=post.sentiment_score,
                direction=direction,
            )

            for symbol in self._seed_demo_symbols(post.text, profile.category):
                if symbol in existing_symbols:
                    continue

                chain_id = self._seed_demo_chain_id(profile.category, symbol)
                contract_address = f"demo:seed:{chain_id}:{symbol.lower()}"
                existing = self.db.execute(
                    select(KOLCall).where(
                        KOLCall.post_id == post.id,
                        KOLCall.chain_id == chain_id,
                        KOLCall.contract_address == contract_address,
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    existing_symbols.add(symbol)
                    continue

                call = KOLCall(
                    kol_id=profile.id,
                    post_id=post.id,
                    chain_id=chain_id,
                    contract_address=contract_address,
                    symbol_text=symbol,
                    direction=direction,
                    confidence=confidence,
                    post_created_at=self._call_timestamp(post),
                    source_mode=post.source_mode,
                    raw_mention_json=self._json_text(
                        {
                            "source": "seed_demo_symbol_fallback",
                            "symbol_text": symbol,
                            "post_id": post.id,
                            "post_sentiment": post.sentiment,
                        }
                    ),
                )
                self.db.add(call)
                existing_symbols.add(symbol)
                calls_created += 1

        return calls_created

    def evaluate_kol_call_prices(self) -> dict[str, Any]:
        rows = self.db.execute(
            select(KOLCall, KOLCallPriceObservation)
            .outerjoin(
                KOLCallPriceObservation,
                KOLCallPriceObservation.kol_call_id == KOLCall.id,
            )
            .order_by(asc(KOLCall.post_created_at), asc(KOLCall.id))
        ).all()

        calls_evaluated = 0
        warnings: list[str] = []

        for call, existing_observation in rows:
            should_attempt = (
                existing_observation is None
                or existing_observation.evaluation_status
                in {PENDING_STATUS, INSUFFICIENT_STATUS, UNRESOLVED_STATUS, ERROR_STATUS}
            )
            if not should_attempt:
                continue

            observation = existing_observation or KOLCallPriceObservation(
                kol_call_id=call.id,
                evaluation_status=PENDING_STATUS,
            )

            try:
                updated = self._evaluate_single_call(call, observation)
                self.db.add(updated)
                calls_evaluated += 1
            except Exception as exc:
                observation.evaluation_status = ERROR_STATUS
                observation.primary_window = None
                observation.primary_return = None
                observation.is_hit = None
                observation.price_source = self._json_text({"error": str(exc)})
                observation.raw_json = self._json_text({"error": str(exc)})
                observation.evaluated_at = self._now()
                self.db.add(observation)
                warnings.append(f"Failed to evaluate KOL call {call.id}: {exc}")

        self._commit_or_rollback(warnings, "Failed to evaluate KOL call prices.")
        return {
            "calls_evaluated": calls_evaluated,
            "warnings": warnings,
        }

    def compute_kol_track_record_scores(self) -> dict[str, Any]:
        profiles = self.db.execute(
            select(KOLProfile).order_by(asc(KOLProfile.priority), asc(KOLProfile.handle))
        ).scalars().all()

        scores_updated = 0
        warnings: list[str] = []

        for profile in profiles:
            rows = self.db.execute(
                select(KOLCall, KOLCallPriceObservation)
                .outerjoin(
                    KOLCallPriceObservation,
                    KOLCallPriceObservation.kol_call_id == KOLCall.id,
                )
                .where(KOLCall.kol_id == profile.id)
                .order_by(desc(KOLCall.post_created_at), desc(KOLCall.id))
            ).all()

            calls = [call for call, _ in rows]
            observations_by_call_id = {
                observation.kol_call_id: observation
                for _, observation in rows
                if observation is not None
            }

            total_calls = len(calls)
            bullish_calls = sum(1 for call in calls if call.direction == "bullish")
            bearish_calls = sum(1 for call in calls if call.direction == "bearish")
            neutral_or_unknown_calls = total_calls - bullish_calls - bearish_calls

            directional_observations = [
                observations_by_call_id[call.id]
                for call in calls
                if call.id in observations_by_call_id
                and call.direction in {"bullish", "bearish"}
                and observations_by_call_id[call.id].evaluation_status == EVALUATED_STATUS
                and observations_by_call_id[call.id].primary_return is not None
            ]

            evaluated_calls = len(directional_observations)
            hits = sum(1 for observation in directional_observations if observation.is_hit is True)
            misses = sum(1 for observation in directional_observations if observation.is_hit is False)
            hit_rate = round(hits / evaluated_calls, 3) if evaluated_calls else None

            returns_24h = [
                float(observation.return_24h)
                for observation in directional_observations
                if observation.return_24h is not None
            ]
            average_return_24h = round(sum(returns_24h) / len(returns_24h), 6) if returns_24h else None
            median_return_24h = round(float(median(returns_24h)), 6) if returns_24h else None

            primary_returns = [
                float(observation.primary_return)
                for observation in directional_observations
                if observation.primary_return is not None
            ]
            average_primary_return = (
                round(sum(primary_returns) / len(primary_returns), 6) if primary_returns else None
            )

            sample_size_confidence = self._sample_size_confidence(evaluated_calls)
            raw_score = self._raw_track_record_score(hit_rate, average_primary_return)
            if evaluated_calls == 0:
                track_record_score = 50.0
            else:
                track_record_score = 50.0 + ((raw_score - 50.0) * sample_size_confidence)
            track_record_score = round(self._clamp(track_record_score, 0.0, 100.0), 2)

            label = self._score_label(
                evaluated_calls=evaluated_calls,
                track_record_score=track_record_score,
            )

            rationale = {
                "primary_window": TRACK_RECORD_WINDOW,
                "methodology": TRACK_RECORD_METHODOLOGY,
                "sample_size_confidence": sample_size_confidence,
                "evaluated_calls": evaluated_calls,
                "hits": hits,
                "misses": misses,
                "hit_rate": hit_rate,
                "average_return_24h": average_return_24h,
                "median_return_24h": median_return_24h,
                "average_primary_return": average_primary_return,
            }

            score = self.db.execute(
                select(KOLTrackRecordScore).where(
                    KOLTrackRecordScore.kol_id == profile.id,
                    KOLTrackRecordScore.window == TRACK_RECORD_WINDOW,
                )
            ).scalar_one_or_none()
            if score is None:
                score = KOLTrackRecordScore(
                    kol_id=profile.id,
                    window=TRACK_RECORD_WINDOW,
                    label=label,
                )

            score.window = TRACK_RECORD_WINDOW
            score.total_calls = total_calls
            score.evaluated_calls = evaluated_calls
            score.bullish_calls = bullish_calls
            score.bearish_calls = bearish_calls
            score.neutral_or_unknown_calls = neutral_or_unknown_calls
            score.hits = hits
            score.misses = misses
            score.hit_rate = hit_rate
            score.average_return_24h = average_return_24h
            score.median_return_24h = median_return_24h
            score.average_primary_return = average_primary_return
            score.sample_size_confidence = sample_size_confidence
            score.track_record_score = track_record_score
            score.label = label
            score.updated_at = self._now()
            score.rationale_json = self._json_text(rationale)
            self.db.add(score)
            scores_updated += 1

        self._commit_or_rollback(warnings, "Failed to compute KOL track record scores.")
        return {
            "scores_updated": scores_updated,
            "warnings": warnings,
        }

    def refresh_kol_performance(self) -> dict[str, Any]:
        call_summary = self.create_kol_calls_from_mentions()
        evaluation_summary = self.evaluate_kol_call_prices()
        score_summary = self.compute_kol_track_record_scores()
        warnings = [
            *call_summary.get("warnings", []),
            *evaluation_summary.get("warnings", []),
            *score_summary.get("warnings", []),
        ]
        return {
            "calls_created": int(call_summary.get("calls_created", 0) or 0),
            "calls_evaluated": int(evaluation_summary.get("calls_evaluated", 0) or 0),
            "scores_updated": int(score_summary.get("scores_updated", 0) or 0),
            "warnings": warnings,
        }

    def list_rankings(
        self,
        *,
        limit: int = 20,
        min_evaluated_calls: int | None = None,
        include_insufficient: bool = True,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit), 100))
        statement = (
            select(KOLTrackRecordScore, KOLProfile)
            .join(KOLProfile, KOLTrackRecordScore.kol_id == KOLProfile.id)
            .where(KOLTrackRecordScore.window == TRACK_RECORD_WINDOW)
        )
        if min_evaluated_calls is not None:
            statement = statement.where(KOLTrackRecordScore.evaluated_calls >= max(0, int(min_evaluated_calls)))
        if not include_insufficient:
            statement = statement.where(KOLTrackRecordScore.evaluated_calls >= 5)

        rows = self.db.execute(
            statement.order_by(
                desc(func.coalesce(KOLTrackRecordScore.track_record_score, 50.0)),
                desc(KOLTrackRecordScore.evaluated_calls),
                asc(KOLProfile.priority),
                asc(KOLProfile.handle),
            ).limit(safe_limit)
        ).all()

        items = [
            self._ranking_item_payload(profile, score)
            for score, profile in rows
        ]
        return {
            "items": items,
            "methodology": TRACK_RECORD_METHODOLOGY,
        }

    def get_track_record(self, *, handle: str) -> dict[str, Any] | None:
        normalized_handle = self._normalize_handle(handle)
        profile = self.db.execute(
            select(KOLProfile).where(KOLProfile.handle == normalized_handle)
        ).scalar_one_or_none()
        if profile is None:
            return None

        score = self.db.execute(
            select(KOLTrackRecordScore)
            .where(
                KOLTrackRecordScore.kol_id == profile.id,
                KOLTrackRecordScore.window == TRACK_RECORD_WINDOW,
            )
            .order_by(desc(KOLTrackRecordScore.updated_at))
            .limit(1)
        ).scalar_one_or_none()

        rows = self.db.execute(
            select(KOLCall, KOLCallPriceObservation, Token)
            .outerjoin(
                KOLCallPriceObservation,
                KOLCallPriceObservation.kol_call_id == KOLCall.id,
            )
            .outerjoin(
                Token,
                (Token.chain_id == KOLCall.chain_id)
                & (Token.contract_address == KOLCall.contract_address),
            )
            .where(KOLCall.kol_id == profile.id)
            .order_by(desc(KOLCall.post_created_at), desc(KOLCall.id))
        ).all()

        recent_calls = [
            self._call_payload(call, observation, token)
            for call, observation, token in rows[:20]
        ]
        evaluated_items = [
            self._call_payload(call, observation, token)
            for call, observation, token in rows
            if observation is not None and observation.evaluation_status == EVALUATED_STATUS
        ]
        pending_items = [
            self._call_payload(call, observation, token)
            for call, observation, token in rows
            if observation is None or observation.evaluation_status in {PENDING_STATUS, INSUFFICIENT_STATUS, UNRESOLVED_STATUS}
        ]

        return {
            "profile": {
                "kol_id": profile.id,
                "handle": profile.handle,
                "display_name": profile.display_name,
                "category": profile.category,
                "priority": profile.priority,
                "notes": profile.notes,
            },
            "score": self._score_payload(score),
            "recent_calls": recent_calls,
            "evaluated_calls": {
                "count": len(evaluated_items),
                "items": evaluated_items[:10],
            },
            "pending_calls": {
                "count": len(pending_items),
                "items": pending_items[:10],
            },
            "methodology": TRACK_RECORD_METHODOLOGY,
            "disclaimer": TRACK_RECORD_DISCLAIMER,
        }

    def get_call_examples(
        self,
        *,
        handle: str | None = None,
        symbol: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit), 100))
        normalized_handle = self._normalize_handle(handle) if handle else None
        normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) and symbol.strip() else None

        statement = (
            select(KOLCall, KOLCallPriceObservation, KOLProfile, Token)
            .join(KOLProfile, KOLCall.kol_id == KOLProfile.id)
            .outerjoin(
                KOLCallPriceObservation,
                KOLCallPriceObservation.kol_call_id == KOLCall.id,
            )
            .outerjoin(
                Token,
                (Token.chain_id == KOLCall.chain_id)
                & (Token.contract_address == KOLCall.contract_address),
            )
            .where(KOLCallPriceObservation.evaluation_status == EVALUATED_STATUS)
        )
        if normalized_handle:
            statement = statement.where(KOLProfile.handle == normalized_handle)
        if normalized_symbol:
            statement = statement.where(
                or_(
                    func.upper(func.coalesce(KOLCall.symbol_text, "")) == normalized_symbol,
                    func.upper(func.coalesce(Token.symbol, "")) == normalized_symbol,
                )
            )

        rows = self.db.execute(
            statement.order_by(desc(KOLCall.post_created_at), desc(KOLCall.id)).limit(safe_limit)
        ).all()

        items = [
            {
                **self._call_payload(call, observation, token),
                "handle": profile.handle,
                "display_name": profile.display_name,
            }
            for call, observation, profile, token in rows
        ]

        return {
            "items": items,
            "match_count": len(items),
            "filters": {
                "handle": normalized_handle,
                "symbol": normalized_symbol,
            },
            "methodology": TRACK_RECORD_METHODOLOGY,
            "disclaimer": TRACK_RECORD_DISCLAIMER,
        }

    def _evaluate_single_call(
        self,
        call: KOLCall,
        observation: KOLCallPriceObservation,
    ) -> KOLCallPriceObservation:
        snapshots = self.db.execute(
            select(TokenSnapshot)
            .where(
                TokenSnapshot.chain_id == call.chain_id,
                TokenSnapshot.contract_address == call.contract_address,
            )
            .order_by(asc(TokenSnapshot.ts))
        ).scalars().all()

        source_map: dict[str, Any] = {}
        raw_payload: dict[str, Any] = {
            "snapshot_count": len(snapshots),
            "post_created_at": self._isoformat(call.post_created_at),
        }

        post_price_point = self._nearest_snapshot_price(
            snapshots,
            target_at=call.post_created_at,
            tolerance=WINDOW_TOLERANCES["post"],
            source_prefix="price_at_post",
        )
        derived_post_point = None
        derived_window_name: str | None = None

        if post_price_point.price is None:
            for candidate_window in ("24h", "1h"):
                derived_post_point = self._derive_post_price_from_window_snapshot(
                    snapshots,
                    post_created_at=call.post_created_at,
                    window_name=candidate_window,
                )
                if derived_post_point.price is not None:
                    derived_window_name = candidate_window
                    break
            if derived_post_point is not None and derived_post_point.price is not None:
                post_price_point = derived_post_point

        window_points: dict[str, PricePoint] = {}
        for window_name, delta in WINDOW_DELTAS.items():
            target_at = call.post_created_at + delta
            window_point = self._nearest_snapshot_price(
                snapshots,
                target_at=target_at,
                tolerance=WINDOW_TOLERANCES[window_name],
                source_prefix=f"price_{window_name}",
            )
            if (
                window_point.price is None
                and derived_window_name == window_name
                and derived_post_point is not None
            ):
                window_point = PricePoint(
                    price=self._window_price_from_derived_snapshot(snapshots, call.post_created_at, window_name),
                    source=f"derived_window_snapshot_{window_name}",
                    observed_at=derived_post_point.observed_at,
                    detail={"derived_from": window_name},
                )
            window_points[window_name] = window_point

        observation.price_at_post = post_price_point.price
        observation.price_1h = window_points["1h"].price
        observation.price_6h = window_points["6h"].price
        observation.price_24h = window_points["24h"].price
        observation.price_7d = window_points["7d"].price

        returns = {
            "1h": self._forward_return(observation.price_at_post, observation.price_1h),
            "6h": self._forward_return(observation.price_at_post, observation.price_6h),
            "24h": self._forward_return(observation.price_at_post, observation.price_24h),
            "7d": self._forward_return(observation.price_at_post, observation.price_7d),
        }
        observation.return_1h = returns["1h"]
        observation.return_6h = returns["6h"]
        observation.return_24h = returns["24h"]
        observation.return_7d = returns["7d"]

        primary_window = self._primary_window(returns)
        primary_return = returns.get(primary_window) if primary_window else None

        observation.primary_window = primary_window
        observation.primary_return = primary_return
        observation.evaluated_at = self._now()

        source_map["price_at_post"] = {
            "source": post_price_point.source,
            "observed_at": self._isoformat(post_price_point.observed_at),
        }
        for window_name, point in window_points.items():
            source_map[f"price_{window_name}"] = {
                "source": point.source,
                "observed_at": self._isoformat(point.observed_at),
            }
        observation.price_source = self._json_text(source_map)

        raw_payload["source_details"] = source_map
        raw_payload["returns"] = returns
        raw_payload["direction"] = call.direction

        now = self._now()
        if call.direction not in {"neutral", "unknown"} and (
            observation.price_at_post is None or primary_return is None
        ):
            demo_evaluated = self._apply_seed_demo_observation(
                call=call,
                observation=observation,
                snapshots=snapshots,
                source_map=source_map,
                raw_payload=raw_payload,
            )
            if demo_evaluated:
                returns = {
                    "1h": observation.return_1h,
                    "6h": observation.return_6h,
                    "24h": observation.return_24h,
                    "7d": observation.return_7d,
                }
                primary_window = observation.primary_window
                primary_return = observation.primary_return

        if call.direction in {"neutral", "unknown"}:
            observation.is_hit = None
            observation.evaluation_status = SKIPPED_NEUTRAL_STATUS
        elif observation.price_at_post is None:
            observation.is_hit = None
            observation.evaluation_status = INSUFFICIENT_STATUS
        elif primary_return is None:
            longest_target = call.post_created_at + WINDOW_DELTAS[TRACK_RECORD_WINDOW]
            observation.is_hit = None
            observation.evaluation_status = PENDING_STATUS if now < longest_target else INSUFFICIENT_STATUS
        else:
            observation.is_hit = self._is_hit(call.direction, primary_return)
            observation.evaluation_status = EVALUATED_STATUS

        observation.price_source = self._json_text(source_map)
        observation.raw_json = self._json_text(raw_payload)
        return observation

    def _apply_seed_demo_observation(
        self,
        *,
        call: KOLCall,
        observation: KOLCallPriceObservation,
        snapshots: list[TokenSnapshot],
        source_map: dict[str, Any],
        raw_payload: dict[str, Any],
    ) -> bool:
        if call.source_mode != "seed":
            return False

        profile = self.db.get(KOLProfile, call.kol_id)
        if profile is None:
            return False

        normalized_handle = self._normalize_handle(profile.handle)
        group = DEMO_KOL_ALIGNMENT_GROUPS.get(normalized_handle)
        if group is None:
            return False

        pattern = DEMO_ALIGNMENT_PATTERNS[group]
        magnitudes = DEMO_ALIGNMENT_MAGNITUDES[group]
        index = max(0, int(call.id or 1) - 1) % len(pattern)
        should_align = pattern[index]
        magnitude = magnitudes[index]

        base_price = next(
            (float(snapshot.price) for snapshot in reversed(snapshots) if snapshot.price is not None),
            1.0,
        )
        anchor_ts = next(
            (self._to_utc(snapshot.ts) for snapshot in reversed(snapshots) if snapshot.ts is not None),
            None,
        )

        if call.direction == "bullish":
            primary_return = magnitude if should_align else -magnitude
        elif call.direction == "bearish":
            primary_return = -magnitude if should_align else magnitude
        else:
            return False

        observation.price_at_post = round(base_price, 12)
        observation.return_1h = round(primary_return * 0.35, 6)
        observation.return_6h = round(primary_return * 0.7, 6)
        observation.return_24h = round(primary_return, 6)
        observation.return_7d = round(primary_return * (1.45 if primary_return >= 0 else 1.15), 6)
        observation.price_1h = round(observation.price_at_post * (1.0 + observation.return_1h), 12)
        observation.price_6h = round(observation.price_at_post * (1.0 + observation.return_6h), 12)
        observation.price_24h = round(observation.price_at_post * (1.0 + observation.return_24h), 12)
        observation.price_7d = round(observation.price_at_post * (1.0 + observation.return_7d), 12)
        observation.primary_window = TRACK_RECORD_WINDOW
        observation.primary_return = observation.return_24h
        observation.evaluated_at = self._now()

        demo_source = {
            "source": "seed_demo_alignment",
            "observed_at": self._isoformat(anchor_ts),
            "group": group,
            "pattern_index": index,
        }
        source_map["price_at_post"] = demo_source
        source_map["price_1h"] = demo_source
        source_map["price_6h"] = demo_source
        source_map["price_24h"] = demo_source
        source_map["price_7d"] = demo_source

        raw_payload["demo_seed_override"] = {
            "enabled": True,
            "handle": normalized_handle,
            "group": group,
            "pattern_index": index,
            "aligned_with_direction": should_align,
        }
        raw_payload["source_details"] = source_map
        raw_payload["returns"] = {
            "1h": observation.return_1h,
            "6h": observation.return_6h,
            "24h": observation.return_24h,
            "7d": observation.return_7d,
        }
        return True

    def _nearest_snapshot_price(
        self,
        snapshots: list[TokenSnapshot],
        *,
        target_at: datetime,
        tolerance: timedelta,
        source_prefix: str,
    ) -> PricePoint:
        if not snapshots:
            return PricePoint(price=None, source=None, observed_at=None, detail={})

        normalized_target = self._to_utc(target_at)
        nearest = min(
            snapshots,
            key=lambda snapshot: abs((self._to_utc(snapshot.ts) - normalized_target).total_seconds()),
        )
        diff = abs(self._to_utc(nearest.ts) - normalized_target)
        if nearest.price is None or diff > tolerance:
            return PricePoint(price=None, source=None, observed_at=None, detail={})

        source = "exact_snapshot" if diff <= timedelta(minutes=10) else "nearest_snapshot"
        return PricePoint(
            price=float(nearest.price),
            source=f"{source_prefix}:{source}",
            observed_at=nearest.ts,
            detail={"diff_seconds": int(diff.total_seconds())},
        )

    def _derive_post_price_from_window_snapshot(
        self,
        snapshots: list[TokenSnapshot],
        *,
        post_created_at: datetime,
        window_name: str,
    ) -> PricePoint:
        percent_field = DERIVABLE_PERCENT_FIELDS.get(window_name)
        if percent_field is None:
            return PricePoint(price=None, source=None, observed_at=None, detail={})

        target_at = self._to_utc(post_created_at + WINDOW_DELTAS[window_name])
        candidates = [
            snapshot
            for snapshot in snapshots
            if getattr(snapshot, percent_field, None) is not None and snapshot.price is not None
        ]
        if not candidates:
            return PricePoint(price=None, source=None, observed_at=None, detail={})

        nearest = min(
            candidates,
            key=lambda snapshot: abs((self._to_utc(snapshot.ts) - target_at).total_seconds()),
        )
        diff = abs(self._to_utc(nearest.ts) - target_at)
        if diff > WINDOW_TOLERANCES[window_name]:
            return PricePoint(price=None, source=None, observed_at=None, detail={})

        percent_change = float(getattr(nearest, percent_field))
        denominator = 1.0 + (percent_change / 100.0)
        if denominator == 0.0:
            return PricePoint(price=None, source=None, observed_at=None, detail={})

        derived_price = float(nearest.price) / denominator
        return PricePoint(
            price=round(derived_price, 12),
            source=f"derived_from_snapshot_{window_name}",
            observed_at=nearest.ts,
            detail={
                "window_name": window_name,
                "snapshot_ts": self._isoformat(nearest.ts),
                "percent_change": percent_change,
            },
        )

    def _window_price_from_derived_snapshot(
        self,
        snapshots: list[TokenSnapshot],
        post_created_at: datetime,
        window_name: str,
    ) -> float | None:
        point = self._nearest_snapshot_price(
            snapshots,
            target_at=post_created_at + WINDOW_DELTAS[window_name],
            tolerance=WINDOW_TOLERANCES[window_name],
            source_prefix=f"price_{window_name}",
        )
        return point.price

    def _ranking_item_payload(
        self,
        profile: KOLProfile,
        score: KOLTrackRecordScore,
    ) -> dict[str, Any]:
        return {
            "kol_id": profile.id,
            "handle": profile.handle,
            "display_name": profile.display_name,
            "category": profile.category,
            "track_record_score": score.track_record_score,
            "label": score.label,
            "total_calls": score.total_calls,
            "evaluated_calls": score.evaluated_calls,
            "hits": score.hits,
            "misses": score.misses,
            "hit_rate": score.hit_rate,
            "average_return_24h": score.average_return_24h,
            "sample_size_confidence": score.sample_size_confidence,
            "explanation": self._ranking_explanation(score),
            "updated_at": self._isoformat(score.updated_at),
        }

    def _ranking_explanation(self, score: KOLTrackRecordScore) -> str:
        if score.evaluated_calls == 0:
            return (
                "This KOL does not yet have enough evaluated bullish or bearish calls in the "
                "tracked dataset to support a historical alignment view."
            )

        if score.sample_size_confidence < 0.6:
            sample_text = "the sample size is still small"
        elif score.sample_size_confidence < 1.0:
            sample_text = "the sample size is still moderate"
        else:
            sample_text = "the sample size is more established"

        if score.track_record_score is not None and score.track_record_score >= 58.0:
            alignment_text = "a positive historical alignment score"
        elif score.track_record_score is not None and score.track_record_score < 42.0:
            alignment_text = "a weaker historical alignment score"
        else:
            alignment_text = "a mixed historical alignment score"

        return (
            f"This KOL currently has {alignment_text} based on evaluated bullish and bearish token "
            f"mentions, and {sample_text}."
        )

    def _score_payload(self, score: KOLTrackRecordScore | None) -> dict[str, Any]:
        if score is None:
            return {
                "window": TRACK_RECORD_WINDOW,
                "track_record_score": 50.0,
                "label": "Insufficient Sample",
                "total_calls": 0,
                "evaluated_calls": 0,
                "bullish_calls": 0,
                "bearish_calls": 0,
                "neutral_or_unknown_calls": 0,
                "hits": 0,
                "misses": 0,
                "hit_rate": None,
                "average_return_24h": None,
                "median_return_24h": None,
                "average_primary_return": None,
                "sample_size_confidence": 0.0,
                "updated_at": None,
                "rationale": {
                    "methodology": TRACK_RECORD_METHODOLOGY,
                },
            }

        return {
            "window": score.window,
            "track_record_score": score.track_record_score,
            "label": score.label,
            "total_calls": score.total_calls,
            "evaluated_calls": score.evaluated_calls,
            "bullish_calls": score.bullish_calls,
            "bearish_calls": score.bearish_calls,
            "neutral_or_unknown_calls": score.neutral_or_unknown_calls,
            "hits": score.hits,
            "misses": score.misses,
            "hit_rate": score.hit_rate,
            "average_return_24h": score.average_return_24h,
            "median_return_24h": score.median_return_24h,
            "average_primary_return": score.average_primary_return,
            "sample_size_confidence": score.sample_size_confidence,
            "updated_at": self._isoformat(score.updated_at),
            "rationale": self._parse_json_text(score.rationale_json) or {},
        }

    def _call_payload(
        self,
        call: KOLCall,
        observation: KOLCallPriceObservation | None,
        token: Token | None,
    ) -> dict[str, Any]:
        chain_meta = build_chain_option(call.chain_id)
        parsed_source = self._parse_json_text(observation.price_source) if observation else None
        return {
            "call_id": call.id,
            "post_id": call.post_id,
            "chain_id": call.chain_id,
            "chain_name": chain_meta["name"],
            "contract_address": call.contract_address,
            "symbol_text": call.symbol_text,
            "token_symbol": token.symbol if token is not None else None,
            "token_name": token.name if token is not None else None,
            "direction": call.direction,
            "confidence": call.confidence,
            "post_created_at": self._isoformat(call.post_created_at),
            "source_mode": call.source_mode,
            "evaluation_status": observation.evaluation_status if observation is not None else PENDING_STATUS,
            "price_at_post": observation.price_at_post if observation is not None else None,
            "price_1h": observation.price_1h if observation is not None else None,
            "price_6h": observation.price_6h if observation is not None else None,
            "price_24h": observation.price_24h if observation is not None else None,
            "price_7d": observation.price_7d if observation is not None else None,
            "return_1h": observation.return_1h if observation is not None else None,
            "return_6h": observation.return_6h if observation is not None else None,
            "return_24h": observation.return_24h if observation is not None else None,
            "return_7d": observation.return_7d if observation is not None else None,
            "primary_return": observation.primary_return if observation is not None else None,
            "primary_window": observation.primary_window if observation is not None else None,
            "is_hit": observation.is_hit if observation is not None else None,
            "price_source": parsed_source,
            "evaluated_at": self._isoformat(observation.evaluated_at) if observation is not None else None,
        }

    def _seed_demo_symbols(self, text: str, category: str | None) -> list[str]:
        matches = re.findall(r"\$([A-Za-z][A-Za-z0-9]{1,9})", text or "")
        symbols: list[str] = []
        seen: set[str] = set()

        for match in matches:
            normalized = match.upper()
            if normalized not in seen:
                seen.add(normalized)
                symbols.append(normalized)

        normalized_category = (category or "").strip().lower()
        fallback_symbols = DEMO_CATEGORY_SYMBOLS.get(
            normalized_category,
            ["BNB", "ETH", "SOL", "AAVE", "PEPE"],
        )
        for fallback_symbol in fallback_symbols:
            if fallback_symbol not in seen:
                seen.add(fallback_symbol)
                symbols.append(fallback_symbol)
            if len(symbols) >= 5:
                break

        return symbols[:5]

    def _seed_demo_chain_id(self, category: str | None, symbol: str) -> str:
        normalized_category = (category or "").strip().lower()
        normalized_symbol = symbol.upper()

        if normalized_category == "solana" or normalized_symbol in {"SOL", "BONK", "WIF", "JUP", "SAM"}:
            return "CT_501"
        if normalized_category == "base" or normalized_symbol in {"BRETT", "AERO"}:
            return "8453"
        return "56"

    def _seed_demo_direction(self, sentiment: str | None, *, text: str, priority: int | None) -> str:
        normalized = self._normalize_direction(sentiment)
        if normalized in {"bullish", "bearish"}:
            return normalized

        lower_text = (text or "").lower()
        bearish_markers = [
            "bearish",
            "don't care",
            "do not care",
            "mixed",
            "skeptical",
            "fade",
            "risk",
            "not bullish",
            "not every",
        ]
        bullish_markers = [
            "bullish",
            "looks better",
            "strength",
            "follow-through",
            "keep pushing",
            "warming up",
            "wakes up",
            "benchmark",
        ]

        if any(marker in lower_text for marker in bearish_markers):
            return "bearish"
        if any(marker in lower_text for marker in bullish_markers):
            return "bullish"

        return "bullish" if (priority or 0) % 2 == 1 else "bearish"

    def _sample_size_confidence(self, evaluated_calls: int) -> float:
        if evaluated_calls <= 0:
            return 0.0
        if evaluated_calls < 5:
            return 0.25
        if evaluated_calls < 10:
            return 0.6
        return 1.0

    def _raw_track_record_score(
        self,
        hit_rate: float | None,
        average_primary_return: float | None,
    ) -> float:
        bounded_component = self._bounded_average_return_component(average_primary_return)
        if hit_rate is None:
            return 50.0 + bounded_component
        return 50.0 + ((float(hit_rate) - 0.5) * 60.0) + bounded_component

    def _bounded_average_return_component(self, average_primary_return: float | None) -> float:
        if average_primary_return is None:
            return 0.0
        return self._clamp(float(average_primary_return) * 200.0, -20.0, 20.0)

    def _score_label(self, *, evaluated_calls: int, track_record_score: float | None) -> str:
        if evaluated_calls <= 0 or track_record_score is None:
            return "Insufficient Sample"
        if track_record_score >= 70.0:
            return "Strong Historical Alignment"
        if track_record_score >= 58.0:
            return "Positive Historical Alignment"
        if track_record_score >= 42.0:
            return "Mixed Historical Alignment"
        return "Weak Historical Alignment"

    def _primary_window(self, returns: dict[str, float | None]) -> str | None:
        if returns.get(TRACK_RECORD_WINDOW) is not None:
            return TRACK_RECORD_WINDOW
        for window_name in ("7d", "6h", "1h"):
            if returns.get(window_name) is not None:
                return window_name
        return None

    def _is_hit(self, direction: str, primary_return: float) -> bool | None:
        if direction == "bullish":
            return primary_return > 0
        if direction == "bearish":
            return primary_return < 0
        return None

    def _forward_return(self, price_at_post: float | None, price_window: float | None) -> float | None:
        if price_at_post is None or price_window is None:
            return None
        if price_at_post == 0:
            return None
        return round((float(price_window) - float(price_at_post)) / float(price_at_post), 6)

    def _normalize_direction(self, value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized in ALLOWED_DIRECTIONS:
            return normalized
        return "unknown"

    def _combined_confidence(
        self,
        mention_confidence: float | None,
        sentiment_score: float | None,
        *,
        direction: str,
    ) -> float:
        values: list[float] = []
        if mention_confidence is not None:
            values.append(self._clamp(float(mention_confidence), 0.0, 1.0))
        if sentiment_score is not None:
            values.append(self._clamp(abs(float(sentiment_score)), 0.0, 1.0))

        if not values:
            base = 0.35 if direction in {"neutral", "unknown"} else 0.5
            return round(base, 3)

        return round(sum(values) / len(values), 3)

    def _call_timestamp(self, post: KOLPost) -> datetime:
        return self._to_utc(post.created_at or post.inserted_at)

    def _normalize_handle(self, value: str | None) -> str:
        normalized = (value or "").strip().lstrip("@").lower()
        return DEMO_KOL_HANDLE_ALIASES.get(normalized, normalized)

    def _commit_or_rollback(self, warnings: list[str], message: str) -> None:
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            warnings.append(f"{message} {exc}")

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _parse_json_text(self, value: str | None) -> Any:
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _json_text(self, value: Any) -> str:
        return json.dumps(value, default=str, separators=(",", ":"))

    def _to_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _isoformat(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return self._to_utc(value).isoformat().replace("+00:00", "Z")

    def _now(self) -> datetime:
        return datetime.now(UTC)


def create_kol_calls_from_mentions(db: Session) -> dict[str, Any]:
    return KOLPerformanceService(db).create_kol_calls_from_mentions()


def evaluate_kol_call_prices(db: Session) -> dict[str, Any]:
    return KOLPerformanceService(db).evaluate_kol_call_prices()


def compute_kol_track_record_scores(db: Session) -> dict[str, Any]:
    return KOLPerformanceService(db).compute_kol_track_record_scores()


def refresh_kol_performance(db: Session) -> dict[str, Any]:
    return KOLPerformanceService(db).refresh_kol_performance()


__all__ = [
    "KOLPerformanceService",
    "TRACK_RECORD_DISCLAIMER",
    "TRACK_RECORD_METHODOLOGY",
    "compute_kol_track_record_scores",
    "create_kol_calls_from_mentions",
    "evaluate_kol_call_prices",
    "refresh_kol_performance",
]
