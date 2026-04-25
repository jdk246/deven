from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import Token
from app.services.scoring import (
    ATTENTION_SCORE_NAME,
    KOLScoreInput,
    ScoringService,
    SmartMoneyScoreInput,
    final_score,
    kol_score,
    market_score,
    safety_score,
    smart_money_score,
)


def test_all_scores_stay_between_zero_and_hundred() -> None:
    now = datetime.now(UTC)
    market_value = market_score(
        volume_24h=1_250_000.0,
        liquidity=650_000.0,
        holders=14_000,
        percent_change_1h=4.2,
        percent_change_24h=17.8,
        top10_holders_pct=0.34,
    )
    kol_value = kol_score(
        mentions=[
            KOLScoreInput(
                created_at=now - timedelta(hours=2),
                sentiment="bullish",
                like_count=120,
                repost_count=35,
                reply_count=18,
                view_count=25_000,
                priority=1,
            )
        ],
        wallet_evidence_count=2,
        now=now,
    )
    smart_money_value = smart_money_score(
        signals=[
            SmartMoneyScoreInput(
                direction="buy",
                smart_money_count=4,
                status="open",
                total_token_value=180_000.0,
                max_gain=22.0,
                exit_rate=0.18,
                signal_trigger_time=now - timedelta(hours=4),
            )
        ],
        smart_money_holding_pct=0.08,
        now=now,
    )
    safety_value = safety_score(
        risk_level_enum="LOW",
        risk_level=10,
        buy_tax=0.0,
        sell_tax=0.0,
        is_verified=True,
        top10_holders_pct=0.28,
        liquidity=750_000.0,
        audit_available=True,
    )
    final_value = final_score(
        market_score_value=market_value,
        kol_score_value=kol_value,
        smart_money_score_value=smart_money_value,
        safety_score_value=safety_value,
    )

    for score in (market_value, kol_value, smart_money_value, safety_value, final_value):
        assert 0.0 <= score <= 100.0


def test_high_audit_risk_lowers_safety_score() -> None:
    low_risk = safety_score(
        risk_level_enum="LOW",
        risk_level=10,
        buy_tax=0.0,
        sell_tax=0.0,
        is_verified=True,
        top10_holders_pct=0.30,
        liquidity=500_000.0,
        audit_available=True,
    )
    high_risk = safety_score(
        risk_level_enum="HIGH",
        risk_level=80,
        buy_tax=0.08,
        sell_tax=0.10,
        is_verified=False,
        top10_holders_pct=0.85,
        liquidity=50_000.0,
        audit_available=True,
    )

    assert high_risk < low_risk


def test_unavailable_audit_data_lowers_safety_score_without_crashing() -> None:
    with_audit = safety_score(
        risk_level_enum="LOW",
        risk_level=10,
        buy_tax=0.0,
        sell_tax=0.0,
        is_verified=True,
        top10_holders_pct=0.25,
        liquidity=400_000.0,
        audit_available=True,
    )
    without_audit = safety_score(
        risk_level_enum=None,
        risk_level=None,
        buy_tax=None,
        sell_tax=None,
        is_verified=None,
        top10_holders_pct=0.25,
        liquidity=400_000.0,
        audit_available=False,
    )

    assert 0.0 <= without_audit <= 100.0
    assert without_audit < with_audit


def test_bullish_mentions_increase_kol_score_and_bearish_mentions_reduce_it() -> None:
    now = datetime.now(UTC)
    bullish_score = kol_score(
        mentions=[
            KOLScoreInput(
                created_at=now - timedelta(hours=1),
                sentiment="bullish",
                like_count=110,
                repost_count=25,
                reply_count=8,
                view_count=18_000,
                priority=1,
            )
        ],
        now=now,
    )
    bearish_score = kol_score(
        mentions=[
            KOLScoreInput(
                created_at=now - timedelta(hours=1),
                sentiment="bearish",
                like_count=110,
                repost_count=25,
                reply_count=8,
                view_count=18_000,
                priority=1,
            )
        ],
        now=now,
    )

    assert bullish_score > bearish_score


def test_high_holder_concentration_penalizes_market_and_safety_scores() -> None:
    diversified_market = market_score(
        volume_24h=900_000.0,
        liquidity=500_000.0,
        holders=12_000,
        percent_change_1h=1.2,
        percent_change_24h=8.0,
        top10_holders_pct=0.25,
    )
    concentrated_market = market_score(
        volume_24h=900_000.0,
        liquidity=500_000.0,
        holders=12_000,
        percent_change_1h=1.2,
        percent_change_24h=8.0,
        top10_holders_pct=0.92,
    )
    diversified_safety = safety_score(
        risk_level_enum="LOW",
        risk_level=8,
        buy_tax=0.0,
        sell_tax=0.0,
        is_verified=True,
        top10_holders_pct=0.25,
        liquidity=500_000.0,
        audit_available=True,
    )
    concentrated_safety = safety_score(
        risk_level_enum="LOW",
        risk_level=8,
        buy_tax=0.0,
        sell_tax=0.0,
        is_verified=True,
        top10_holders_pct=0.92,
        liquidity=500_000.0,
        audit_available=True,
    )

    assert concentrated_market < diversified_market
    assert concentrated_safety < diversified_safety


def test_scoring_service_handles_missing_market_fields_and_uses_attention_score_name(db_session) -> None:
    db_session.add(
        Token(
            chain_id="56",
            contract_address="0x9999999999999999999999999999999999999999",
            symbol="TRACE",
            name="Trust Trace",
            decimals=18,
        )
    )
    db_session.commit()

    breakdown = ScoringService(db_session).score_token(
        chain_id="56",
        contract_address="0x9999999999999999999999999999999999999999",
        persist=False,
    )

    assert breakdown.score_name == ATTENTION_SCORE_NAME
    assert "Buy" not in breakdown.score_name
    assert 0.0 <= breakdown.market_score <= 100.0
    assert 0.0 <= breakdown.attention_score <= 100.0
