from __future__ import annotations

import re

from app.services.chat_agent import ChatAgentService
from tests.helpers import make_agent_tool_result


class RankingRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, input_args: dict | None = None):
        args = input_args or {}
        self.calls.append((tool_name, dict(args)))

        if tool_name == "rank_kols_by_track_record":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="rank_kols_by_track_record",
                source="internal_context_db",
                input_args=args,
                data={
                    "items": [
                        {
                            "handle": "alpha_calls",
                            "track_record_score": 68.0,
                            "label": "Positive Historical Alignment",
                            "evaluated_calls": 5,
                            "sample_size_confidence": 0.6,
                        },
                        {
                            "handle": "beta_calls",
                            "track_record_score": 32.0,
                            "label": "Weak Historical Alignment",
                            "evaluated_calls": 5,
                            "sample_size_confidence": 0.6,
                        },
                    ],
                    "methodology": "KOL rankings are based on post-event token movement after tracked KOL mentions.",
                },
            )

        if tool_name == "get_kol_track_record":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_kol_track_record",
                source="internal_context_db",
                input_args=args,
                data={
                    "profile": {"handle": "beta_calls", "display_name": "Beta Calls"},
                    "score": {
                        "track_record_score": 32.0,
                        "label": "Weak Historical Alignment",
                        "evaluated_calls": 5,
                        "hits": 1,
                        "misses": 4,
                        "hit_rate": 0.2,
                        "sample_size_confidence": 0.6,
                    },
                },
            )

        if tool_name == "get_kol_call_examples":
            return make_agent_tool_result(
                skill_name="internal_database_context",
                tool_name="get_kol_call_examples",
                source="internal_context_db",
                input_args=args,
                data={
                    "items": [
                        {
                            "handle": "beta_calls",
                            "direction": "bullish",
                            "token_symbol": "BNB",
                            "primary_window": "24h",
                            "primary_return": -0.07,
                            "is_hit": False,
                        }
                    ]
                },
            )

        raise AssertionError(f"Unhandled tool call: {tool_name}")


def test_agent_answers_kol_ranking_questions_without_defamatory_language(db_session) -> None:
    registry = RankingRegistry()
    service = ChatAgentService(db_session, registry=registry)
    questions = [
        "Which KOLs have the best track record?",
        "Rank the KOLs.",
        "Why does @beta_calls have a low score?",
        "How do you calculate KOL rankings?",
    ]

    for question in questions:
        response = service.answer_question(message=question, debug=True)

        assert set(response) == {"answer", "evidence_used", "missing_data", "tool_trace", "disclaimer"}
        assert response["answer"]
        assert response["evidence_used"]
        assert isinstance(response["missing_data"], list)
        assert response["tool_trace"]
        assert response["disclaimer"]
        assert not re.search(r"\b(buy|sell)\b", response["answer"], re.IGNORECASE)
        assert not re.search(r"\b(fake|fraud|scammer)\b", response["answer"], re.IGNORECASE)

    called_tools = {tool_name for tool_name, _ in registry.calls}
    assert {"rank_kols_by_track_record", "get_kol_track_record", "get_kol_call_examples"}.issubset(
        called_tools
    )
