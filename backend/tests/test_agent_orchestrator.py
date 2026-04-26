from __future__ import annotations

import re

import pytest

from app.models import Token, TokenInsight
from app.services.chat_agent import ChatAgentService
from tests.helpers import make_agent_tool_result


class RecordingRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    @staticmethod
    def _symbol_name_for_args(args: dict) -> tuple[str, str]:
        contract_address = (args.get("contract_address") or "").lower()
        if contract_address == "0xtrump000000000000000000000000000000000000":
            return "MAGA", "Official Trump"
        if args.get("chain_id") == "CT_501":
            return "SOL", "Solana"
        return "BNB", "BNB"

    async def call_tool(self, tool_name: str, input_args: dict | None = None):
        args = input_args or {}
        self.calls.append((tool_name, dict(args)))

        if tool_name == "crypto_market_rank":
            return make_agent_tool_result(
                skill_name="crypto_market_rank",
                tool_name="trending_token_rank",
                source="binance_skills",
                input_args=args,
                data={"items": [{"symbol": "BNB", "contractAddress": "0xbnb"}], "match_count": 1},
            )

        if tool_name == "get_trending_token_context":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_trending_token_context",
                source="internal_context_db",
                input_args=args,
                data={
                    "items": [
                        {
                            "symbol": "BNB",
                            "chain_short_name": "BSC",
                            "attention_score": 82.0,
                            "smart_money_signal_count": 3,
                            "kol_mention_count": 4,
                            "volume_24h": 1_600_000.0,
                        }
                    ],
                    "match_count": 1,
                    "data_mode": "seed",
                },
            )

        if tool_name == "query_token_info":
            symbol, name = self._symbol_name_for_args(args)
            return make_agent_tool_result(
                skill_name="query_token_info",
                tool_name="token_info_bundle",
                source="binance_skills",
                input_args=args,
                data={
                    "metadata": {"symbol": symbol, "name": name},
                    "dynamic_market_data": {
                        "price": 11.5 if symbol == "MAGA" else (650.0 if symbol == "BNB" else 155.0),
                        "percentChange24h": 18.4 if symbol == "MAGA" else (6.2 if symbol == "BNB" else 5.4),
                        "volume24h": 1_900_000.0,
                        "liquidity": 780_000.0,
                    },
                },
            )

        if tool_name == "query_token_audit":
            return make_agent_tool_result(
                skill_name="query_token_audit",
                tool_name="token_audit",
                source="binance_skills",
                input_args=args,
                data={
                    "riskLevelEnum": "LOW",
                    "extraInfo": {"isVerified": True, "buyTax": 0.0, "sellTax": 0.0},
                },
            )

        if tool_name == "search_kol_mentions":
            symbol, name = self._symbol_name_for_args(args)
            handle = "ansem_demo" if symbol == "SOL" else ("meme_marshal" if symbol == "MAGA" else "raoul_pal_demo")
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="search_kol_mentions",
                source="internal_context_db",
                input_args=args,
                data={
                    "items": [
                        {
                            "handle": handle,
                            "display_name": handle.replace("_", " ").title(),
                            "sentiment": "bullish",
                            "chain_id": args.get("chain_id"),
                            "token_symbol": symbol,
                            "token_name": name,
                            "engagement": {
                                "like_count": 120,
                                "repost_count": 24,
                                "reply_count": 8,
                                "view_count": 22_000,
                            },
                        }
                    ],
                    "match_count": 1,
                },
            )

        if tool_name == "get_latest_insight":
            symbol, name = self._symbol_name_for_args(args)
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_latest_insight",
                source="internal_context_db",
                input_args=args,
                data={
                    "insight": {
                        "summary": f"{name} has attention because local KOL context and market activity are aligned while risk stays manageable.",
                        "attention_score": 78.0,
                        "market_score": 74.0,
                        "kol_score": 72.0,
                        "smart_money_score": 66.0,
                        "safety_score": 81.0,
                        "label": "Watchlist",
                    }
                },
            )

        if tool_name == "get_high_risk_tokens":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_high_risk_tokens",
                source="internal_context_db",
                input_args=args,
                data={
                    "items": [
                        {
                            "symbol": "BNB",
                            "chain_short_name": "BSC",
                            "risk_index": 63.0,
                            "safety_score": 41.0,
                            "risk_flags": ["liquidity is on the lighter side"],
                        }
                    ],
                    "match_count": 1,
                },
            )

        if tool_name == "get_kol_summary":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_kol_summary",
                source="internal_context_db",
                input_args=args,
                data={
                    "items": [
                        {
                            "handle": "ansem_demo",
                            "display_name": "Ansem (Demo)",
                            "category": "solana",
                            "priority": 3,
                            "stats": {"post_count": 2, "resolved_mention_count": 2},
                        }
                    ],
                    "match_count": 1,
                },
            )

        if tool_name == "trading_signal":
            return make_agent_tool_result(
                skill_name="trading_signal",
                tool_name="smart_money_signals",
                source="binance_skills",
                input_args=args,
                data={"signal_count": 2, "positive_count": 2, "negative_count": 0, "items": []},
            )

        if tool_name == "get_token_context":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_token_context",
                source="internal_context_db",
                input_args=args,
                data={
                    "smart_money_summary": {
                        "signal_count": 2,
                        "positive_signal_count": 2,
                        "negative_signal_count": 0,
                    },
                    "mention_summary": {"mention_count": 3},
                    "latest_market_snapshot": {"percent_change_24h": 6.1},
                },
            )

        if tool_name == "get_data_mode_status":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_data_mode_status",
                source="internal_context_db",
                input_args=args,
                data={"kol_data_mode": "seed", "record_counts": {"tokens": 2}},
            )

        raise AssertionError(f"Unhandled tool call in test registry: {tool_name}")


def _seed_agent_tokens(db_session) -> None:
    db_session.add_all(
        [
            Token(
                chain_id="56",
                contract_address="0xbnb000000000000000000000000000000000000",
                symbol="BNB",
                name="BNB",
                decimals=18,
            ),
            Token(
                chain_id="CT_501",
                contract_address="So11111111111111111111111111111111111111112",
                symbol="SOL",
                name="Solana",
                decimals=9,
            ),
            Token(
                chain_id="56",
                contract_address="0xtrump000000000000000000000000000000000000",
                symbol="MAGA",
                name="Official Trump",
                decimals=18,
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            TokenInsight(
                chain_id="56",
                contract_address="0xbnb000000000000000000000000000000000000",
                market_score=74.0,
                kol_score=72.0,
                smart_money_score=66.0,
                safety_score=81.0,
                final_score=78.0,
                label="Watchlist",
                summary="BNB summary",
            ),
            TokenInsight(
                chain_id="CT_501",
                contract_address="So11111111111111111111111111111111111111112",
                market_score=73.0,
                kol_score=71.0,
                smart_money_score=64.0,
                safety_score=79.0,
                final_score=76.0,
                label="Watchlist",
                summary="SOL summary",
            ),
            TokenInsight(
                chain_id="56",
                contract_address="0xtrump000000000000000000000000000000000000",
                market_score=79.0,
                kol_score=68.0,
                smart_money_score=61.0,
                safety_score=72.0,
                final_score=74.0,
                label="Watchlist",
                summary="Official Trump summary",
            ),
        ]
    )
    db_session.commit()


@pytest.mark.parametrize(
    ("question", "chain_id", "expected_tools"),
    [
        ("Which tokens are trending?", None, {"crypto_market_rank", "get_trending_token_context"}),
        ("Which tokens are trending right now?", None, {"crypto_market_rank", "get_trending_token_context"}),
        ("Why is BNB trending?", "56", {"query_token_info", "query_token_audit", "search_kol_mentions", "get_latest_insight"}),
        ("Which tokens look risky?", None, {"get_high_risk_tokens"}),
        ("Which KOLs mentioned SOL?", None, {"search_kol_mentions", "get_kol_summary"}),
        ("Is the KOL hype backed by market data?", None, {"crypto_market_rank", "get_trending_token_context"}),
    ],
)
def test_agent_orchestrator_uses_expected_tools(db_session, question, chain_id, expected_tools) -> None:
    _seed_agent_tokens(db_session)
    registry = RecordingRegistry()
    service = ChatAgentService(db_session, registry=registry)

    response = service.answer_question(message=question, chain_id=chain_id, debug=True)

    assert set(response) == {"answer", "evidence_used", "missing_data", "tool_trace", "disclaimer"}
    assert isinstance(response["answer"], str) and response["answer"]
    assert isinstance(response["evidence_used"], list)
    assert isinstance(response["missing_data"], list)
    assert isinstance(response["tool_trace"], list)
    assert response["disclaimer"]

    called_tools = {tool_name for tool_name, _ in registry.calls}
    assert expected_tools.issubset(called_tools)
    assert not re.search(r"\b(should buy|buy now|should sell|sell now)\b", response["answer"], re.IGNORECASE)
    assert not re.search(r"\b(guaranteed profit|risk-free|safe token)\b", response["answer"], re.IGNORECASE)


def test_agent_orchestrator_infers_plain_english_token_reference(db_session) -> None:
    _seed_agent_tokens(db_session)
    registry = RecordingRegistry()
    service = ChatAgentService(db_session, registry=registry)

    response = service.answer_question(
        message="How is that Donald Trump meme coin doing?",
        chain_id="56",
        debug=True,
    )

    called_tools = {tool_name for tool_name, _ in registry.calls}
    assert {"query_token_info", "query_token_audit", "search_kol_mentions", "get_latest_insight"}.issubset(called_tools)
    assert "highest-attention stored token" not in response["answer"].lower()
    assert "official trump" in response["answer"].lower() or "maga" in response["answer"].lower()
    assert response["disclaimer"]


def test_agent_orchestrator_does_not_fallback_to_top_attention_for_unknown_token(db_session) -> None:
    _seed_agent_tokens(db_session)
    registry = RecordingRegistry()
    service = ChatAgentService(db_session, registry=registry)

    response = service.answer_question(
        message="Why is that penguin coin trending?",
        chain_id="56",
        debug=True,
    )

    assert response["missing_data"] == ["specific_token"]
    assert "highest-attention stored token" not in response["answer"].lower()
    assert "could not confidently map" in response["answer"].lower()
    assert registry.calls == []


def test_agent_orchestrator_handles_parody_token_spelling(db_session) -> None:
    db_session.add(
        Token(
            chain_id="CT_501",
            contract_address="0xtromp000000000000000000000000000000000000",
            symbol="DUNALD",
            name="Dunald Tromp",
            decimals=9,
        )
    )
    db_session.flush()
    db_session.add(
        TokenInsight(
            chain_id="CT_501",
            contract_address="0xtromp000000000000000000000000000000000000",
            market_score=71.0,
            kol_score=64.0,
            smart_money_score=58.0,
            safety_score=69.0,
            final_score=73.0,
            label="Watchlist",
            summary="Dunald Tromp summary",
        )
    )
    db_session.commit()

    class ParodyRegistry(RecordingRegistry):
        @staticmethod
        def _symbol_name_for_args(args: dict) -> tuple[str, str]:
            contract_address = (args.get("contract_address") or "").lower()
            if contract_address == "0xtromp000000000000000000000000000000000000":
                return "DUNALD", "Dunald Tromp"
            return RecordingRegistry._symbol_name_for_args(args)

    registry = ParodyRegistry()
    service = ChatAgentService(db_session, registry=registry)

    response = service.answer_question(
        message="How is that Donald Trump meme coin doing?",
        chain_id="CT_501",
        debug=True,
    )

    called_tools = {tool_name for tool_name, _ in registry.calls}
    assert {"query_token_info", "query_token_audit", "search_kol_mentions", "get_latest_insight"}.issubset(called_tools)
    assert "highest-attention stored token" not in response["answer"].lower()
    assert "dunald tromp" in response["answer"].lower()
