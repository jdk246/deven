from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

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
from app.services.kol_performance import KOLPerformanceService
from tests.helpers import seed_kol_performance_history


def _seed_single_case(
    db_session,
    *,
    handle: str = "case_kol",
    symbol: str = "BNB",
    chain_id: str = "56",
    contract_address: str = "0x56000000000000000000000000000000000000aa",
    direction: str = "bullish",
    return_24h: float = 0.1,
    with_prices: bool = True,
) -> None:
    profile = KOLProfile(
        handle=handle,
        display_name=handle.replace("_", " ").title(),
        category="tests",
        priority=1,
    )
    db_session.add(profile)
    db_session.add(
        Token(
            chain_id=chain_id,
            contract_address=contract_address,
            symbol=symbol,
            name=f"{symbol} Token",
            decimals=18 if chain_id == "56" else 9,
        )
    )
    db_session.flush()

    created_at = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
    post = KOLPost(
        kol_id=profile.id,
        external_post_id=f"{handle}-post",
        created_at=created_at,
        text=f"{handle} is {direction} on ${symbol}",
        url=f"https://example.com/{handle}",
        like_count=10,
        repost_count=4,
        reply_count=1,
        view_count=500,
        source_mode="seed",
        sentiment=direction,
        sentiment_score=0.9 if direction == "bullish" else (-0.9 if direction == "bearish" else 0.0),
    )
    db_session.add(post)
    db_session.flush()

    db_session.add(
        TokenMention(
            post_id=post.id,
            chain_id=chain_id,
            contract_address=contract_address,
            symbol_text=symbol,
            mention_type="cashtag",
            sentiment=direction,
            confidence=0.9,
            is_resolved=True,
        )
    )

    if with_prices:
        db_session.add_all(
            [
                TokenSnapshot(
                    chain_id=chain_id,
                    contract_address=contract_address,
                    ts=created_at,
                    price=100.0,
                ),
                TokenSnapshot(
                    chain_id=chain_id,
                    contract_address=contract_address,
                    ts=created_at + timedelta(hours=24),
                    price=100.0 * (1.0 + return_24h),
                    percent_change_24h=return_24h * 100.0,
                ),
            ]
        )
    db_session.commit()


def test_resolved_mentions_create_kol_calls_without_duplicates(db_session) -> None:
    _seed_single_case(db_session)
    service = KOLPerformanceService(db_session)

    first = service.create_kol_calls_from_mentions()
    second = service.create_kol_calls_from_mentions()

    calls = db_session.execute(select(KOLCall)).scalars().all()
    assert first["calls_created"] == 1
    assert second["calls_created"] == 0
    assert len(calls) == 1


def test_bullish_positive_return_is_hit(db_session) -> None:
    _seed_single_case(db_session, direction="bullish", return_24h=0.1)
    service = KOLPerformanceService(db_session)
    service.create_kol_calls_from_mentions()
    service.evaluate_kol_call_prices()

    observation = db_session.execute(select(KOLCallPriceObservation)).scalar_one()
    assert observation.evaluation_status == "evaluated"
    assert observation.is_hit is True


def test_bullish_negative_return_is_miss(db_session) -> None:
    _seed_single_case(db_session, direction="bullish", return_24h=-0.1)
    service = KOLPerformanceService(db_session)
    service.create_kol_calls_from_mentions()
    service.evaluate_kol_call_prices()

    observation = db_session.execute(select(KOLCallPriceObservation)).scalar_one()
    assert observation.evaluation_status == "evaluated"
    assert observation.is_hit is False


def test_bearish_negative_return_is_hit(db_session) -> None:
    _seed_single_case(
        db_session,
        direction="bearish",
        return_24h=-0.08,
        contract_address="0x56000000000000000000000000000000000000bb",
    )
    service = KOLPerformanceService(db_session)
    service.create_kol_calls_from_mentions()
    service.evaluate_kol_call_prices()

    observation = db_session.execute(select(KOLCallPriceObservation)).scalar_one()
    assert observation.evaluation_status == "evaluated"
    assert observation.is_hit is True


def test_bearish_positive_return_is_miss(db_session) -> None:
    _seed_single_case(
        db_session,
        direction="bearish",
        return_24h=0.08,
        contract_address="0x56000000000000000000000000000000000000cc",
    )
    service = KOLPerformanceService(db_session)
    service.create_kol_calls_from_mentions()
    service.evaluate_kol_call_prices()

    observation = db_session.execute(select(KOLCallPriceObservation)).scalar_one()
    assert observation.evaluation_status == "evaluated"
    assert observation.is_hit is False


def test_neutral_call_is_skipped_from_hit_rate(db_session) -> None:
    _seed_single_case(
        db_session,
        direction="neutral",
        return_24h=0.05,
        contract_address="0x56000000000000000000000000000000000000dd",
    )
    service = KOLPerformanceService(db_session)
    service.create_kol_calls_from_mentions()
    service.evaluate_kol_call_prices()
    service.compute_kol_track_record_scores()

    observation = db_session.execute(select(KOLCallPriceObservation)).scalar_one()
    score = db_session.execute(select(KOLTrackRecordScore)).scalar_one()
    assert observation.evaluation_status == "skipped_neutral"
    assert observation.is_hit is None
    assert score.evaluated_calls == 0


def test_missing_price_data_produces_insufficient_status(db_session) -> None:
    _seed_single_case(
        db_session,
        with_prices=False,
        contract_address="0x56000000000000000000000000000000000000ee",
    )
    service = KOLPerformanceService(db_session)
    service.create_kol_calls_from_mentions()
    service.evaluate_kol_call_prices()

    observation = db_session.execute(select(KOLCallPriceObservation)).scalar_one()
    assert observation.evaluation_status == "insufficient_price_data"


def test_sample_size_confidence_reduces_extreme_scores(db_session) -> None:
    seed_kol_performance_history(db_session)
    service = KOLPerformanceService(db_session)
    service.refresh_kol_performance()

    scores = dict(
        db_session.execute(
            select(KOLProfile.handle, KOLTrackRecordScore)
            .join(KOLTrackRecordScore, KOLTrackRecordScore.kol_id == KOLProfile.id)
        ).all()
    )
    gamma_score = scores["gamma_calls"]
    alpha_score = scores["alpha_calls"]

    assert gamma_score.sample_size_confidence == 0.25
    assert 50.0 < gamma_score.track_record_score < alpha_score.track_record_score


def test_track_record_score_is_always_bounded_between_zero_and_hundred(db_session) -> None:
    seed_kol_performance_history(db_session)
    service = KOLPerformanceService(db_session)
    service.refresh_kol_performance()

    scores = db_session.execute(select(KOLTrackRecordScore)).scalars().all()
    assert scores
    assert all(0.0 <= float(score.track_record_score or 50.0) <= 100.0 for score in scores)
