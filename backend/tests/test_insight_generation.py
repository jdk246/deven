from __future__ import annotations

from datetime import UTC, datetime

from app.models import Token, TokenAudit, TokenSnapshot
from app.services.insight_generation import InsightGenerationService


def test_insight_generation_uses_full_token_name_in_summary(db_session) -> None:
    db_session.add(
        Token(
            chain_id="CT_501",
            contract_address="6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
            symbol="TRUMP",
            name="OFFICIAL TRUMP",
            decimals=9,
        )
    )
    db_session.add(
        TokenSnapshot(
            chain_id="CT_501",
            contract_address="6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
            ts=datetime(2026, 4, 26, 11, 10, tzinfo=UTC),
            price=11.2,
            percent_change_24h=-10.08,
            volume_24h=46_740_000.0,
            liquidity=66_480_000.0,
            holders=12_500,
            top10_holders_pct=0.88,
        )
    )
    db_session.add(
        TokenAudit(
            chain_id="CT_501",
            contract_address="6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
            ts=datetime(2026, 4, 26, 10, 50, tzinfo=UTC),
            has_result=True,
            is_supported=True,
            risk_level_enum="LOW",
            risk_level=18,
            buy_tax=0.0,
            sell_tax=0.0,
            is_verified=True,
        )
    )
    db_session.commit()

    insight = InsightGenerationService(db_session).generate_token_insight(
        chain_id="CT_501",
        contract_address="6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
        persist=False,
    )

    assert insight.summary.startswith("OFFICIAL TRUMP (TRUMP) on SOL falls in the ")
    assert "Attention Score" in insight.summary
