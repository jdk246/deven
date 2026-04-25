from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.schemas import AgentToolResult
from app.models import KOLPost, KOLProfile, Token, TokenMention, TokenSnapshot


def make_agent_tool_result(
    *,
    skill_name: str,
    tool_name: str,
    source: str,
    data: Any = None,
    status: str = "ok",
    input_args: dict[str, Any] | None = None,
    error: str | None = None,
    latency_ms: int = 7,
) -> AgentToolResult:
    return AgentToolResult(
        skill_name=skill_name,
        tool_name=tool_name,
        input_args=input_args or {},
        source=source,
        status=status,
        latency_ms=latency_ms,
        fetched_at=datetime.now(UTC),
        data=data,
        error=error,
    )


def seed_kol_performance_history(db, *, start_at: datetime | None = None) -> dict[str, Any]:
    base_time = start_at or datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    tokens = {
        "BNB": ("56", "0x5600000000000000000000000000000000000001", "BNB"),
        "SOL": ("CT_501", "So11111111111111111111111111111111111111112", "SOL"),
        "PEPE": ("56", "0x5600000000000000000000000000000000000002", "PEPE"),
    }

    for chain_id, contract_address, symbol in tokens.values():
        db.merge(
            Token(
                chain_id=chain_id,
                contract_address=contract_address,
                symbol=symbol,
                name=f"{symbol} Token",
                decimals=18 if chain_id == "56" else 9,
            )
        )

    alpha = KOLProfile(
        handle="alpha_calls",
        display_name="Alpha Calls",
        category="macro",
        priority=1,
        notes="Synthetic positive alignment history for tests.",
    )
    beta = KOLProfile(
        handle="beta_calls",
        display_name="Beta Calls",
        category="momentum",
        priority=2,
        notes="Synthetic weaker alignment history for tests.",
    )
    gamma = KOLProfile(
        handle="gamma_calls",
        display_name="Gamma Calls",
        category="altcoins",
        priority=3,
        notes="Synthetic low-sample history for tests.",
    )
    db.add_all([alpha, beta, gamma])
    db.flush()

    call_rows = [
        (alpha, "BNB", "bullish", 0.12),
        (alpha, "SOL", "bearish", -0.08),
        (alpha, "PEPE", "bullish", 0.18),
        (alpha, "BNB", "bullish", 0.05),
        (alpha, "SOL", "bearish", -0.03),
        (beta, "BNB", "bullish", -0.07),
        (beta, "SOL", "bearish", 0.04),
        (beta, "PEPE", "bullish", -0.12),
        (beta, "BNB", "bearish", 0.06),
        (beta, "SOL", "bullish", -0.02),
        (gamma, "PEPE", "bullish", 0.25),
        (gamma, "SOL", "bearish", -0.01),
    ]

    for index, (profile, token_key, direction, return_24h) in enumerate(call_rows):
        post_created_at = base_time + timedelta(days=index * 2)
        chain_id, contract_address, symbol = tokens[token_key]
        post = KOLPost(
            kol_id=profile.id,
            external_post_id=f"{profile.handle}-{index}",
            created_at=post_created_at,
            text=f"{profile.handle} is {direction} on ${symbol}",
            url=f"https://example.com/{profile.handle}/{index}",
            like_count=100 + index,
            repost_count=20 + index,
            reply_count=5 + index,
            view_count=2_000 + index * 50,
            source_mode="seed",
            sentiment=direction,
            sentiment_score=0.8 if direction == "bullish" else -0.8,
        )
        db.add(post)
        db.flush()

        db.add(
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

        price_at_post = 100.0 + index
        price_24h = round(price_at_post * (1.0 + return_24h), 6)
        db.add_all(
            [
                TokenSnapshot(
                    chain_id=chain_id,
                    contract_address=contract_address,
                    ts=post_created_at,
                    price=price_at_post,
                ),
                TokenSnapshot(
                    chain_id=chain_id,
                    contract_address=contract_address,
                    ts=post_created_at + timedelta(hours=24),
                    price=price_24h,
                    percent_change_24h=return_24h * 100.0,
                ),
            ]
        )

    db.commit()
    return {
        "base_time": base_time,
        "handles": [alpha.handle, beta.handle, gamma.handle],
        "tokens": tokens,
    }
