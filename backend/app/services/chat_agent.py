from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any, Literal

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.agent_tools.registry import ToolRegistry
from app.config import get_settings
from app.models import AgentRun, ChatLog, Token, TokenInsight
from app.schemas import AgentToolResult
from app.services.market_ingestion import build_chain_option
from app.services.scoring import ATTENTION_SCORE_NAME

CHAT_DISCLAIMER = "This is market research only and not financial advice."
DEFAULT_LIMIT = 10
MAX_GENERIC_KOL_MENTIONS = 50

EVM_ADDRESS_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
CASHTAG_PATTERN = re.compile(r"\$([A-Za-z][A-Za-z0-9]{1,14})\b")
HANDLE_PATTERN = re.compile(r"@([A-Za-z0-9_]{1,32})")
WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z0-9]{1,14}\b")

TOKEN_STOPWORDS = {
    "a",
    "about",
    "activity",
    "and",
    "are",
    "attention",
    "backed",
    "based",
    "bullish",
    "by",
    "compare",
    "current",
    "data",
    "does",
    "explain",
    "for",
    "general",
    "have",
    "help",
    "historical",
    "history",
    "hype",
    "is",
    "it",
    "kol",
    "low",
    "look",
    "looks",
    "market",
    "methodology",
    "mentioned",
    "money",
    "now",
    "of",
    "on",
    "or",
    "performance",
    "performed",
    "positive",
    "rank",
    "ranking",
    "rankings",
    "record",
    "right",
    "risk",
    "risky",
    "sample",
    "score",
    "scores",
    "sentiment",
    "smart",
    "social",
    "supported",
    "the",
    "this",
    "track",
    "token",
    "tokens",
    "trending",
    "vs",
    "weak",
    "what",
    "which",
    "why",
    "with",
    "worst",
    "best",
    "today",
    "latest",
    "coin",
    "coins",
    "meme",
    "memecoin",
    "crypto",
    "project",
    "doing",
}

TOKEN_QUERY_STOPWORDS = TOKEN_STOPWORDS | {
    "coin",
    "coins",
    "memecoin",
    "memecoins",
    "meme",
    "crypto",
    "project",
    "projects",
    "ticker",
    "tickers",
    "official",
    "doing",
    "about",
    "that",
}

TOKEN_ALIAS_HINTS: dict[str, tuple[str, ...]] = {
    "donald trump": ("TRUMP", "OFFICIAL TRUMP"),
    "trump meme coin": ("TRUMP", "OFFICIAL TRUMP"),
    "donald trump meme coin": ("TRUMP", "OFFICIAL TRUMP"),
    "official trump": ("TRUMP", "OFFICIAL TRUMP"),
    "trump coin": ("TRUMP",),
    "dog with hat": ("WIF", "DOGWIFHAT"),
    "dogwifhat": ("WIF", "DOGWIFHAT"),
    "frog coin": ("PEPE", "PEPE"),
}

ChatIntent = Literal[
    "trending_tokens",
    "token_screening",
    "token_explanation",
    "kol_sentiment",
    "kol_rankings",
    "kol_track_record",
    "kol_performance_methodology",
    "kol_call_examples",
    "high_risk_tokens",
    "smart_money_activity",
    "compare_tokens",
    "general_help",
]


@dataclass(frozen=True)
class ResolvedToken:
    chain_id: str
    contract_address: str
    symbol: str | None
    name: str | None
    chain_name: str
    chain_short_name: str
    attention_score: float | None = None


@dataclass(frozen=True)
class TokenResolution:
    tokens: tuple[ResolvedToken, ...]
    ambiguous_symbols: tuple[str, ...]
    warning: str | None = None


@dataclass(frozen=True)
class ToolPlanStep:
    alias: str
    tool_name: str
    input_args: dict[str, Any]


@dataclass(frozen=True)
class ToolCallRecord:
    alias: str
    tool_name: str
    input_args: dict[str, Any]
    result: AgentToolResult


class ChatAgentService:
    def __init__(
        self,
        db: Session,
        *,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.db = db
        self.registry = registry or ToolRegistry(db=db)

    def answer_question(
        self,
        *,
        message: str,
        chain_id: str | None = None,
        token_context: dict[str, Any] | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        started_at = time.perf_counter()
        cleaned_message = message.strip()
        effective_chain_id = chain_id or self._context_string((token_context or {}).get("chain_id"))
        normalized_intent: ChatIntent = "general_help"

        if not cleaned_message:
            response = self._response(
                answer="Please send a question so I can look up the stored token data.",
                evidence_used=[],
                missing_data=["user_question"],
                tool_calls=[],
                debug=debug,
            )
            total_latency_ms = self._latency_ms(started_at)
            self._store_logs(
                request_id=request_id,
                message="",
                normalized_intent=normalized_intent,
                response=response,
                full_tool_trace=[],
                total_latency_ms=total_latency_ms,
                status="error",
            )
            return response

        normalized_intent = self._classify_intent(
            cleaned_message,
            token_context=token_context,
        )
        payload = self._dispatch_intent(
            intent=normalized_intent,
            message=cleaned_message,
            chain_id=effective_chain_id,
            token_context=token_context,
        )
        response = self._response(
            answer=payload["answer"],
            evidence_used=payload["evidence_used"],
            missing_data=payload["missing_data"],
            tool_calls=payload["tool_calls"],
            debug=debug,
        )
        full_tool_trace = self._full_tool_trace(payload["tool_calls"])
        total_latency_ms = self._latency_ms(started_at)
        run_status = self._derive_run_status(payload["tool_calls"], payload["missing_data"])
        self._store_logs(
            request_id=request_id,
            message=cleaned_message,
            normalized_intent=normalized_intent,
            response=response,
            full_tool_trace=full_tool_trace,
            total_latency_ms=total_latency_ms,
            status=run_status,
        )
        return response

    def _dispatch_intent(
        self,
        *,
        intent: ChatIntent,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if intent == "trending_tokens":
            return self._answer_trending_tokens(message=message, chain_id=chain_id)
        if intent == "token_screening":
            return self._answer_token_screening(message=message, chain_id=chain_id)
        if intent == "token_explanation":
            return self._answer_token_explanation(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
            )
        if intent == "kol_sentiment":
            return self._answer_kol_sentiment(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
            )
        if intent == "kol_rankings":
            return self._answer_kol_rankings(message=message)
        if intent == "kol_track_record":
            return self._answer_kol_track_record(message=message)
        if intent == "kol_performance_methodology":
            return self._answer_kol_performance_methodology()
        if intent == "kol_call_examples":
            return self._answer_kol_call_examples(message=message)
        if intent == "high_risk_tokens":
            return self._answer_high_risk_tokens(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
            )
        if intent == "smart_money_activity":
            return self._answer_smart_money_activity(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
            )
        if intent == "compare_tokens":
            return self._answer_compare_tokens(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
            )
        return self._answer_general_help(chain_id=chain_id)

    def _answer_trending_tokens(
        self,
        *,
        message: str,
        chain_id: str | None,
    ) -> dict[str, Any]:
        plan = [
            ToolPlanStep(
                alias="live_trending_rank",
                tool_name="crypto_market_rank",
                input_args={
                    "chain_id": chain_id,
                    "mode": "trending_tokens",
                    "size": DEFAULT_LIMIT,
                },
            ),
            ToolPlanStep(
                alias="local_trending_context",
                tool_name="get_trending_token_context",
                input_args={
                    "chain_id": chain_id,
                    "limit": DEFAULT_LIMIT,
                },
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        live_result = self._result_for_alias(tool_calls, "live_trending_rank")
        local_result = self._result_for_alias(tool_calls, "local_trending_context")
        local_items = self._sorted_local_trending_items(self._tool_items(local_result))
        live_items = self._tool_items(live_result)

        answer_parts: list[str] = []
        missing_data: list[str] = []

        if local_items:
            top_labels = self._format_item_list(local_items[:3])
            answer_parts.append(
                f"The strongest current attention in the local dataset is around {top_labels}."
            )
        else:
            answer_parts.append(
                "I do not have strong local trending context yet."
            )
            missing_data.append("local_trending_context")

        if live_result is not None and live_result.status in {"ok", "partial"}:
            answer_parts.append(
                f"Binance live rank returned {len(live_items)} current item"
                f"{'' if len(live_items) == 1 else 's'} for this view."
            )
        else:
            missing_data.append("live_binance_trending_rank")
            answer_parts.append(
                "Live Binance trending rank was unavailable, so this answer leans on stored data."
            )

        evidence = [
            self._local_trending_evidence(local_result),
            self._live_rank_evidence(live_result, evidence_type="live_trending_rank"),
        ]
        return self._result_payload(
            answer=" ".join(answer_parts).strip(),
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_token_screening(
        self,
        *,
        message: str,
        chain_id: str | None,
    ) -> dict[str, Any]:
        effective_chain_id = chain_id or self._infer_chain_id_from_message(message)
        plan = [
            ToolPlanStep(
                alias="screening_context",
                tool_name="get_trending_token_context",
                input_args={
                    "chain_id": effective_chain_id,
                    "limit": DEFAULT_LIMIT,
                },
            )
        ]
        tool_calls = self._run_tool_plan(plan)
        context_result = self._result_for_alias(tool_calls, "screening_context")
        items = self._sorted_local_trending_items(self._tool_items(context_result))

        if not items:
            return self._result_payload(
                answer="I do not have enough stored token context to screen that market slice right now.",
                evidence_used=[item for item in [self._local_trending_evidence(context_result)] if item is not None],
                missing_data=["screening_context"],
                tool_calls=tool_calls,
            )

        requested_chain_name = (
            build_chain_option(effective_chain_id)["name"] if effective_chain_id else "the current tracked set"
        )
        requested_criteria = self._screening_requested_criteria(message)
        minimum_hits = max(2, min(3, len(requested_criteria))) if requested_criteria else 2

        analyses: list[dict[str, Any]] = []
        for item in items:
            analysis = self._screening_analysis(item)
            analysis["score"] = self._screening_score(item=item, analysis=analysis)
            analyses.append(analysis)

        analyses.sort(
            key=lambda row: (
                float(row.get("score") or 0.0),
                float(row.get("attention_score") or 0.0),
                float(row.get("liquidity") or 0.0),
            ),
            reverse=True,
        )

        matching_items = [analysis for analysis in analyses if int(analysis["matched_criteria_count"]) >= minimum_hits]
        shortlisted = (matching_items or analyses)[:3]

        if not shortlisted:
            return self._result_payload(
                answer="I could not identify any stored tokens that are a reasonable fit for that screen right now.",
                evidence_used=[item for item in [self._local_trending_evidence(context_result)] if item is not None],
                missing_data=["screening_matches"],
                tool_calls=tool_calls,
            )

        if matching_items:
            lead = (
                f"Within {requested_chain_name}, the strongest current matches for that screen are "
                f"{self._format_list([analysis['label'] for analysis in shortlisted])}."
            )
            missing_data: list[str] = []
        else:
            lead = (
                f"I do not see three perfect matches for all of those filters in {requested_chain_name} right now, "
                f"but the closest current fits are {self._format_list([analysis['label'] for analysis in shortlisted])}."
            )
            missing_data = ["strict_screen_matches"]

        ranked_bits = [
            f"{index}. {self._screening_summary(analysis)}"
            for index, analysis in enumerate(shortlisted, start=1)
        ]

        answer = " ".join([lead, *ranked_bits]).strip()
        evidence = [
            self._local_trending_evidence(context_result),
            self._screening_evidence(
                chain_name=requested_chain_name,
                requested_criteria=requested_criteria,
                shortlisted=shortlisted,
                used_fallback=not bool(matching_items),
            ),
        ]
        return self._result_payload(
            answer=answer,
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_token_explanation(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resolution = self._resolve_tokens(
            message=message,
            chain_id=chain_id,
            token_context=token_context,
            max_tokens=1,
            allow_fallback=True,
        )
        if resolution.ambiguous_symbols and not resolution.tokens:
            return self._ambiguous_token_payload(resolution)

        if not resolution.tokens:
            if self._asks_for_generic_market_support(message):
                return self._answer_market_support_overview(chain_id=chain_id)
            return self._result_payload(
                answer=(
                    "I could not confidently map that question to one tracked token. "
                    "Try the symbol, contract address, or a more specific token name."
                ),
                evidence_used=[],
                missing_data=["specific_token"],
                tool_calls=[],
            )

        token = resolution.tokens[0]
        plan = [
            ToolPlanStep(
                alias="live_token_info",
                tool_name="query_token_info",
                input_args={
                    "chain_id": token.chain_id,
                    "contract_address": token.contract_address,
                    "include_dynamic": True,
                },
            ),
            ToolPlanStep(
                alias="live_token_audit",
                tool_name="query_token_audit",
                input_args={
                    "chain_id": token.chain_id,
                    "contract_address": token.contract_address,
                },
            ),
            ToolPlanStep(
                alias="local_kol_mentions",
                tool_name="search_kol_mentions",
                input_args={
                    "chain_id": token.chain_id,
                    "contract_address": token.contract_address,
                    "query": token.symbol or token.name or token.contract_address,
                    "limit": DEFAULT_LIMIT,
                },
            ),
            ToolPlanStep(
                alias="local_latest_insight",
                tool_name="get_latest_insight",
                input_args={
                    "chain_id": token.chain_id,
                    "contract_address": token.contract_address,
                },
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        info_result = self._result_for_alias(tool_calls, "live_token_info")
        audit_result = self._result_for_alias(tool_calls, "live_token_audit")
        mentions_result = self._result_for_alias(tool_calls, "local_kol_mentions")
        insight_result = self._result_for_alias(tool_calls, "local_latest_insight")

        dynamic_market = self._tool_dynamic_market_data(info_result)
        insight = self._tool_nested_dict(insight_result, "insight")
        mention_items = self._tool_items(mentions_result)
        mention_breakdown = self._mention_breakdown(mention_items)
        audit_data = self._tool_dict(audit_result)

        answer_parts: list[str] = []
        if resolution.warning:
            answer_parts.append(resolution.warning)

        if insight and insight.get("summary"):
            answer_parts.append(self._present_insight_summary(token, insight))
        else:
            answer_parts.append(
                f"{self._token_label(token)} is in the local dataset, but I do not have a stored insight summary for it yet."
            )

        mention_clause = self._token_mention_clause(token, mention_breakdown)
        if mention_clause:
            answer_parts.append(mention_clause)

        market_clause = self._market_clause(dynamic_market)
        if market_clause:
            answer_parts.append(market_clause)

        risk_clause = self._risk_clause(audit_data, insight)
        if risk_clause:
            answer_parts.append(risk_clause)

        missing_data: list[str] = []
        if not insight:
            missing_data.append("insight_summary")
        if mention_breakdown["mention_count"] == 0:
            missing_data.append("kol_mentions")
        if not dynamic_market:
            missing_data.append("live_market_data")
        if not audit_data:
            missing_data.append("live_audit_data")

        evidence = [
            self._insight_evidence(token, insight_result),
            self._kol_mention_evidence(token, mention_items, mentions_result),
            self._market_evidence(token, dynamic_market, info_result),
            self._audit_evidence(token, audit_data, insight, audit_result),
        ]
        return self._result_payload(
            answer=" ".join(part for part in answer_parts if part).strip(),
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_market_support_overview(
        self,
        *,
        chain_id: str | None,
    ) -> dict[str, Any]:
        plan = [
            ToolPlanStep(
                alias="live_trending_rank",
                tool_name="crypto_market_rank",
                input_args={
                    "chain_id": chain_id,
                    "mode": "trending_tokens",
                    "size": DEFAULT_LIMIT,
                },
            ),
            ToolPlanStep(
                alias="local_trending_context",
                tool_name="get_trending_token_context",
                input_args={
                    "chain_id": chain_id,
                    "limit": DEFAULT_LIMIT,
                },
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        live_result = self._result_for_alias(tool_calls, "live_trending_rank")
        local_result = self._result_for_alias(tool_calls, "local_trending_context")
        local_items = self._sorted_local_trending_items(self._tool_items(local_result))
        supported_items = [
            item
            for item in local_items
            if int(item.get("kol_mention_count") or 0) > 0
            and (
                float(item.get("volume_24h") or 0.0) > 0.0
                or float(item.get("liquidity") or 0.0) > 0.0
            )
        ]
        answer_parts: list[str] = []
        missing_data: list[str] = []

        if supported_items:
            answer_parts.append(
                "In the current tracked dataset, the clearest cases where social attention is backed by market activity are "
                f"{self._format_item_list(supported_items[:3])}."
            )
        else:
            answer_parts.append(
                "I do not see a strong market-backed social setup in the stored dataset right now."
            )
            missing_data.append("market_backed_social_context")

        if live_result is not None and live_result.status in {"ok", "partial"}:
            answer_parts.append(
                f"Live Binance trending rank returned {len(self._tool_items(live_result))} item"
                f"{'' if len(self._tool_items(live_result)) == 1 else 's'}, which helps cross-check that read."
            )
        else:
            answer_parts.append(
                "Live Binance trending rank was unavailable, so this answer leans more heavily on stored local context."
            )
            missing_data.append("live_binance_trending_rank")

        evidence = [
            self._local_trending_evidence(local_result),
            self._live_rank_evidence(live_result, evidence_type="live_trending_rank"),
        ]
        return self._result_payload(
            answer=" ".join(answer_parts).strip(),
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_kol_sentiment(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        handle = self._extract_handles(message)
        resolved = self._resolve_tokens(
            message=message,
            chain_id=chain_id,
            token_context=token_context,
            max_tokens=1,
            allow_fallback=False,
        )
        primary_token = resolved.tokens[0] if resolved.tokens else None
        query_text = self._derived_query_text(message, primary_token)

        plan = [
            ToolPlanStep(
                alias="kol_mentions_search",
                tool_name="search_kol_mentions",
                input_args={
                    "query": None if primary_token and primary_token.symbol else query_text,
                    "chain_id": primary_token.chain_id if primary_token else chain_id,
                    "contract_address": primary_token.contract_address if primary_token else None,
                    "handle": handle[0] if handle else None,
                    "limit": MAX_GENERIC_KOL_MENTIONS,
                },
            ),
            ToolPlanStep(
                alias="kol_summary",
                tool_name="get_kol_summary",
                input_args={
                    "handle": handle[0] if handle else None,
                    "limit": DEFAULT_LIMIT,
                },
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        mentions_result = self._result_for_alias(tool_calls, "kol_mentions_search")
        summary_result = self._result_for_alias(tool_calls, "kol_summary")
        mention_items = self._tool_items(mentions_result)

        if handle:
            profile = self._tool_nested_dict(summary_result, "profile")
            stats = self._tool_nested_dict(summary_result, "stats")
            answer = self._handle_specific_kol_answer(
                handle=handle[0],
                profile=profile,
                stats=stats,
                mention_items=mention_items,
            )
            evidence = [
                self._kol_profile_evidence(summary_result),
                self._kol_search_evidence(mentions_result, mention_items),
            ]
            missing_data = self._kol_missing_data(summary_result, mention_items)
            return self._result_payload(
                answer=answer,
                evidence_used=[item for item in evidence if item is not None],
                missing_data=missing_data,
                tool_calls=tool_calls,
            )

        if self._asks_for_handles(message):
            grouped = self._group_mentions_by_handle(mention_items)
            if grouped:
                top_handles = list(grouped.values())[:5]
                answer = (
                    f"The KOLs most clearly mentioning {query_text or primary_token.symbol or 'that token'} "
                    f"are {self._format_handle_groups(top_handles)}."
                )
                evidence = [
                    self._kol_search_evidence(mentions_result, mention_items),
                    self._kol_summary_list_evidence(summary_result),
                ]
                missing_data = self._kol_missing_data(summary_result, mention_items)
            else:
                answer = "I do not see matching KOL mentions for that query in the local database."
                evidence = [self._kol_summary_list_evidence(summary_result)]
                missing_data = ["kol_mentions"]
            return self._result_payload(
                answer=answer,
                evidence_used=[item for item in evidence if item is not None],
                missing_data=missing_data,
                tool_calls=tool_calls,
            )

        grouped_tokens = self._group_mentions_by_token(mention_items)
        positive_tokens = [
            item for item in grouped_tokens.values() if item["bullish"] > item["bearish"]
        ]
        positive_tokens.sort(
            key=lambda item: (
                item["bullish"] - item["bearish"],
                item["mentions"],
                item["engagement"],
            ),
            reverse=True,
        )

        if positive_tokens:
            answer = (
                "The strongest positive KOL sentiment in the local dataset is around "
                f"{self._format_token_groups(positive_tokens[:3])}."
            )
            evidence = [
                self._kol_search_evidence(mentions_result, mention_items),
                self._kol_summary_list_evidence(summary_result),
            ]
            missing_data = self._kol_missing_data(summary_result, mention_items)
        else:
            answer = (
                "I do not see a strong positive KOL skew in the current local mentions. "
                "Most mapped chatter is either sparse, neutral, or mixed."
            )
            evidence = [self._kol_summary_list_evidence(summary_result)]
            missing_data = ["positive_kol_signal"]

        return self._result_payload(
            answer=answer,
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_high_risk_tokens(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resolution = self._resolve_tokens(
            message=message,
            chain_id=chain_id,
            token_context=token_context,
            max_tokens=1,
            allow_fallback=True,
        )
        plan = [
            ToolPlanStep(
                alias="high_risk_tokens",
                tool_name="get_high_risk_tokens",
                input_args={
                    "chain_id": chain_id,
                    "limit": DEFAULT_LIMIT,
                },
            )
        ]
        tool_calls = self._run_tool_plan(plan)
        risk_result = self._result_for_alias(tool_calls, "high_risk_tokens")
        items = self._tool_items(risk_result)

        if resolution.tokens:
            token = resolution.tokens[0]
            matched = next(
                (
                    item
                    for item in items
                    if item.get("chain_id") == token.chain_id
                    and item.get("contract_address") == token.contract_address
                ),
                None,
            )
            if matched is not None:
                answer = (
                    f"{self._token_label(token)} does look risky in the stored dataset. "
                    f"The main warnings are {self._format_risk_flags(matched.get('risk_flags') or [])}, "
                    f"and the safety score is {self._score_text(matched.get('safety_score'))}."
                )
                evidence = [self._specific_risk_evidence(matched, risk_result)]
                missing_data = []
            else:
                answer = (
                    f"{self._token_label(token)} is not among the highest-risk tokens in the current local ranking."
                )
                evidence = [self._risk_list_evidence(risk_result)]
                missing_data = ["specific_high_risk_match"]
            return self._result_payload(
                answer=answer,
                evidence_used=[item for item in evidence if item is not None],
                missing_data=missing_data,
                tool_calls=tool_calls,
            )

        if items:
            answer = (
                "The riskiest stored tokens right now look like "
                f"{self._format_item_list(items[:3])}. "
                "They rank that way because of weaker safety scores and concrete audit or liquidity warnings."
            )
            evidence = [self._risk_list_evidence(risk_result)]
            missing_data = []
        else:
            answer = "I do not see any especially risky tokens in the current local dataset."
            evidence = []
            missing_data = ["high_risk_tokens"]
        return self._result_payload(
            answer=answer,
            evidence_used=evidence,
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_smart_money_activity(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resolution = self._resolve_tokens(
            message=message,
            chain_id=chain_id,
            token_context=token_context,
            max_tokens=1,
            allow_fallback=True,
        )

        if resolution.tokens:
            token = resolution.tokens[0]
            plan = [
                ToolPlanStep(
                    alias="live_trading_signal",
                    tool_name="trading_signal",
                    input_args={
                        "chain_id": token.chain_id,
                        "contract_address": token.contract_address,
                        "page_size": DEFAULT_LIMIT,
                    },
                ),
                ToolPlanStep(
                    alias="stored_token_context",
                    tool_name="get_token_context",
                    input_args={
                        "chain_id": token.chain_id,
                        "contract_address": token.contract_address,
                        "limit": DEFAULT_LIMIT,
                    },
                ),
            ]
            tool_calls = self._run_tool_plan(plan)
            signal_result = self._result_for_alias(tool_calls, "live_trading_signal")
            context_result = self._result_for_alias(tool_calls, "stored_token_context")
            signal_data = self._tool_dict(signal_result)
            smart_money_summary = self._tool_nested_dict(context_result, "smart_money_summary")
            answer = self._specific_smart_money_answer(
                token=token,
                signal_data=signal_data,
                smart_money_summary=smart_money_summary,
            )
            evidence = [
                self._smart_money_signal_evidence(signal_result, token),
                self._stored_smart_money_evidence(context_result, token),
            ]
            missing_data = self._smart_money_missing_data(signal_data, smart_money_summary)
            return self._result_payload(
                answer=answer,
                evidence_used=[item for item in evidence if item is not None],
                missing_data=missing_data,
                tool_calls=tool_calls,
            )

        effective_chain_id = chain_id or self._default_chain_id()
        plan = [
            ToolPlanStep(
                alias="smart_money_inflow_rank",
                tool_name="crypto_market_rank",
                input_args={
                    "chain_id": effective_chain_id,
                    "mode": "smart_money_inflow_rank",
                    "period": "24h",
                },
            ),
            ToolPlanStep(
                alias="local_trending_context",
                tool_name="get_trending_token_context",
                input_args={
                    "chain_id": effective_chain_id,
                    "limit": DEFAULT_LIMIT,
                },
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        inflow_result = self._result_for_alias(tool_calls, "smart_money_inflow_rank")
        local_result = self._result_for_alias(tool_calls, "local_trending_context")
        inflow_items = self._tool_items(inflow_result)
        local_items = [
            item
            for item in self._sorted_local_trending_items(self._tool_items(local_result))
            if int(item.get("smart_money_signal_count") or 0) > 0
        ]

        answer_parts: list[str] = []
        missing_data: list[str] = []
        if inflow_items:
            answer_parts.append(
                f"Live smart-money inflow rank is strongest around {self._format_live_rank_list(inflow_items[:3])}."
            )
        else:
            answer_parts.append(
                "Live smart-money inflow rank was unavailable, so I am leaning on stored context."
            )
            missing_data.append("live_smart_money_rank")

        if local_items:
            answer_parts.append(
                f"In the stored dataset, the clearest smart-money activity is around {self._format_item_list(local_items[:3])}."
            )
        else:
            answer_parts.append(
                "The stored dataset does not currently show strong smart-money activity."
            )
            missing_data.append("stored_smart_money_context")

        evidence = [
            self._live_rank_evidence(inflow_result, evidence_type="smart_money_inflow_rank"),
            self._local_trending_evidence(local_result),
        ]
        return self._result_payload(
            answer=" ".join(answer_parts).strip(),
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_compare_tokens(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resolution = self._resolve_tokens(
            message=message,
            chain_id=chain_id,
            token_context=token_context,
            max_tokens=2,
            allow_fallback=False,
        )
        if resolution.ambiguous_symbols and len(resolution.tokens) < 2:
            return self._ambiguous_token_payload(resolution)
        if len(resolution.tokens) < 2:
            return self._result_payload(
                answer="Please specify two tracked tokens to compare.",
                evidence_used=[],
                missing_data=["compare_tokens"],
                tool_calls=[],
            )

        left, right = resolution.tokens[:2]
        plan = [
            ToolPlanStep(
                alias="left_insight",
                tool_name="get_latest_insight",
                input_args={
                    "chain_id": left.chain_id,
                    "contract_address": left.contract_address,
                },
            ),
            ToolPlanStep(
                alias="right_insight",
                tool_name="get_latest_insight",
                input_args={
                    "chain_id": right.chain_id,
                    "contract_address": right.contract_address,
                },
            ),
            ToolPlanStep(
                alias="left_context",
                tool_name="get_token_context",
                input_args={
                    "chain_id": left.chain_id,
                    "contract_address": left.contract_address,
                    "limit": DEFAULT_LIMIT,
                },
            ),
            ToolPlanStep(
                alias="right_context",
                tool_name="get_token_context",
                input_args={
                    "chain_id": right.chain_id,
                    "contract_address": right.contract_address,
                    "limit": DEFAULT_LIMIT,
                },
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        left_insight = self._tool_nested_dict(self._result_for_alias(tool_calls, "left_insight"), "insight")
        right_insight = self._tool_nested_dict(self._result_for_alias(tool_calls, "right_insight"), "insight")
        left_context = self._tool_dict(self._result_for_alias(tool_calls, "left_context"))
        right_context = self._tool_dict(self._result_for_alias(tool_calls, "right_context"))

        answer = self._comparison_answer(
            left=left,
            right=right,
            left_insight=left_insight,
            right_insight=right_insight,
            left_context=left_context,
            right_context=right_context,
        )
        evidence = [
            self._comparison_evidence(left, left_insight, left_context),
            self._comparison_evidence(right, right_insight, right_context),
        ]
        missing_data: list[str] = []
        if not left_insight:
            missing_data.append("left_insight")
        if not right_insight:
            missing_data.append("right_insight")
        if not left_context:
            missing_data.append("left_context")
        if not right_context:
            missing_data.append("right_context")

        return self._result_payload(
            answer=answer,
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_kol_rankings(self, *, message: str) -> dict[str, Any]:
        lowered = message.lower()
        wants_low_alignment = any(
            phrase in lowered
            for phrase in (
                "weak historical alignment",
                "historically bad",
                "lowest score",
                "low score",
                "worst",
                "negative post-event alignment",
            )
        )
        plan = [
            ToolPlanStep(
                alias="kol_rankings",
                tool_name="rank_kols_by_track_record",
                input_args={
                    "limit": DEFAULT_LIMIT,
                    "min_evaluated_calls": 1,
                    "include_insufficient": True,
                },
            )
        ]
        tool_calls = self._run_tool_plan(plan)
        rankings_result = self._result_for_alias(tool_calls, "kol_rankings")
        rankings_payload = self._tool_dict(rankings_result)
        items = self._tool_items(rankings_result)

        if not items:
            return self._result_payload(
                answer=(
                    "I do not have enough evaluated KOL call history yet to rank historical alignment. "
                    "Once more post-event price observations are available, these rankings will fill in."
                ),
                evidence_used=[],
                missing_data=["kol_rankings"],
                tool_calls=tool_calls,
            )

        ranked_items = sorted(
            items,
            key=lambda item: (
                float(item.get("track_record_score") or 50.0),
                float(item.get("sample_size_confidence") or 0.0),
                int(item.get("evaluated_calls") or 0),
            ),
            reverse=not wants_low_alignment,
        )
        selected = ranked_items[:3]
        labels = [
            (
                f"@{item.get('handle')} "
                f"({item.get('label')}, "
                f"score {float(item.get('track_record_score') or 50.0):.1f}, "
                f"{int(item.get('evaluated_calls') or 0)} evaluated call"
                f"{'' if int(item.get('evaluated_calls') or 0) == 1 else 's'})"
            )
            for item in selected
            if item.get("handle")
        ]
        stance = (
            "the weakest historical alignment in the evaluated dataset currently looks like"
            if wants_low_alignment
            else "among evaluated KOL calls, the strongest historical alignment currently looks like"
        )
        answer = (
            f"{stance} {self._format_list(labels)}. "
            "The score reflects whether bullish or bearish token mentions were followed by price movement in the same direction, "
            "primarily over the 24h window, with sample-size adjustment so tiny histories do not get extreme scores."
        )
        evidence = [
            {
                "type": "kol_rankings",
                "status": rankings_result.status if rankings_result is not None else "unknown",
                "top_ranked_handles": [item.get("handle") for item in selected],
                "evaluated_calls": [int(item.get("evaluated_calls") or 0) for item in selected],
                "scores": [float(item.get("track_record_score") or 50.0) for item in selected],
                "methodology": rankings_payload.get("methodology"),
            }
        ]
        return self._result_payload(
            answer=answer,
            evidence_used=evidence,
            missing_data=[],
            tool_calls=tool_calls,
        )

    def _answer_kol_track_record(self, *, message: str) -> dict[str, Any]:
        handles = self._extract_handles(message)
        if not handles:
            return self._result_payload(
                answer="Please name a KOL handle like @example so I can look up that track record.",
                evidence_used=[],
                missing_data=["kol_handle"],
                tool_calls=[],
            )

        handle = handles[0]
        plan = [
            ToolPlanStep(
                alias="kol_track_record",
                tool_name="get_kol_track_record",
                input_args={"handle": handle},
            ),
            ToolPlanStep(
                alias="kol_call_examples",
                tool_name="get_kol_call_examples",
                input_args={"handle": handle, "limit": 4},
            ),
        ]
        tool_calls = self._run_tool_plan(plan)
        track_record_result = self._result_for_alias(tool_calls, "kol_track_record")
        examples_result = self._result_for_alias(tool_calls, "kol_call_examples")
        track_payload = self._tool_dict(track_record_result)
        profile = track_payload.get("profile") if isinstance(track_payload.get("profile"), dict) else {}
        score = track_payload.get("score") if isinstance(track_payload.get("score"), dict) else {}
        examples = self._tool_items(examples_result)

        if not profile:
            return self._result_payload(
                answer=f"I do not have a stored track record for @{handle}.",
                evidence_used=[],
                missing_data=["kol_track_record"],
                tool_calls=tool_calls,
            )

        evaluated_calls = int(score.get("evaluated_calls") or 0)
        label = str(score.get("label") or "Insufficient Sample")
        sample_confidence = float(score.get("sample_size_confidence") or 0.0)
        score_value = float(score.get("track_record_score") or 50.0)
        hits = int(score.get("hits") or 0)
        misses = int(score.get("misses") or 0)
        hit_rate = self._to_float(score.get("hit_rate"))

        if evaluated_calls <= 0:
            answer = (
                f"@{profile.get('handle')} is in the tracked dataset, but there is not enough evaluated bullish or bearish "
                "history yet to support a strong track record read."
            )
            missing_data = ["evaluated_kol_calls"]
        else:
            hit_rate_text = f"{hit_rate * 100:.1f}%" if hit_rate is not None else "n/a"
            answer = (
                f"@{profile.get('handle')} currently has {label.lower()} with a track record score of {score_value:.1f} "
                f"across {evaluated_calls} evaluated bullish or bearish calls, with {hits} hit"
                f"{'' if hits == 1 else 's'}, {misses} miss"
                f"{'' if misses == 1 else 'es'}, and a {hit_rate_text} hit rate. "
                f"Sample-size confidence is {sample_confidence:.2f}, so {self._sample_size_text(sample_confidence)}."
            )
            missing_data = []

        example_text = self._format_kol_call_examples(examples[:2])
        if example_text:
            answer += f" Recent evaluated examples include {example_text}."

        evidence = [
            {
                "type": "kol_track_record",
                "status": track_record_result.status if track_record_result is not None else "unknown",
                "handle": profile.get("handle"),
                "label": label,
                "track_record_score": score_value,
                "evaluated_calls": evaluated_calls,
                "hits": hits,
                "misses": misses,
                "sample_size_confidence": sample_confidence,
            },
            {
                "type": "kol_call_examples",
                "status": examples_result.status if examples_result is not None else "unknown",
                "match_count": len(examples),
            },
        ]
        return self._result_payload(
            answer=answer,
            evidence_used=evidence,
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _answer_kol_performance_methodology(self) -> dict[str, Any]:
        plan = [
            ToolPlanStep(
                alias="kol_rankings",
                tool_name="rank_kols_by_track_record",
                input_args={
                    "limit": 3,
                    "min_evaluated_calls": None,
                    "include_insufficient": True,
                },
            )
        ]
        tool_calls = self._run_tool_plan(plan)
        rankings_result = self._result_for_alias(tool_calls, "kol_rankings")
        methodology = self._tool_dict(rankings_result).get("methodology")
        answer = (
            "KOL rankings are based on post-event token movement after tracked KOL mentions. "
            "Bullish calls count as aligned when forward returns are positive, bearish calls count as aligned when forward returns are negative, "
            "and neutral or unknown calls are stored but excluded from hit-rate scoring. "
            "The primary window is 24h when available, with 1h, 6h, and 7d stored alongside it. "
            "Scores are blended back toward neutral when sample size is small, so tiny histories do not get extreme rankings. "
            "This is correlation-based and not proof of causation."
        )
        evidence = [
            {
                "type": "kol_ranking_methodology",
                "status": rankings_result.status if rankings_result is not None else "unknown",
                "methodology": methodology,
            }
        ]
        return self._result_payload(
            answer=answer,
            evidence_used=evidence,
            missing_data=[],
            tool_calls=tool_calls,
        )

    def _answer_kol_call_examples(self, *, message: str) -> dict[str, Any]:
        handles = self._extract_handles(message)
        symbols = [match.group(1).upper() for match in CASHTAG_PATTERN.finditer(message)]
        plan = [
            ToolPlanStep(
                alias="kol_call_examples",
                tool_name="get_kol_call_examples",
                input_args={
                    "handle": handles[0] if handles else None,
                    "symbol": symbols[0] if symbols else None,
                    "limit": 5,
                },
            )
        ]
        tool_calls = self._run_tool_plan(plan)
        examples_result = self._result_for_alias(tool_calls, "kol_call_examples")
        items = self._tool_items(examples_result)

        if not items:
            return self._result_payload(
                answer="I do not have evaluated KOL call examples that match that filter yet.",
                evidence_used=[],
                missing_data=["kol_call_examples"],
                tool_calls=tool_calls,
            )

        answer = (
            "Here are a few evaluated KOL call examples from the tracked dataset: "
            f"{self._format_kol_call_examples(items[:3])}. "
            "These examples describe historical post-event alignment only, not proof of causation."
        )
        evidence = [
            {
                "type": "kol_call_examples",
                "status": examples_result.status if examples_result is not None else "unknown",
                "match_count": len(items),
                "handles": list(dict.fromkeys(item.get("handle") for item in items if item.get("handle")))[:5],
            }
        ]
        return self._result_payload(
            answer=answer,
            evidence_used=evidence,
            missing_data=[],
            tool_calls=tool_calls,
        )

    def _answer_general_help(self, *, chain_id: str | None) -> dict[str, Any]:
        plan = [
            ToolPlanStep(
                alias="data_mode_status",
                tool_name="get_data_mode_status",
                input_args={},
            )
        ]
        tool_calls = self._run_tool_plan(plan)
        status_result = self._result_for_alias(tool_calls, "data_mode_status")
        status_data = self._tool_dict(status_result)
        record_counts = status_data.get("record_counts") if isinstance(status_data, dict) else {}
        data_mode = status_data.get("kol_data_mode") if isinstance(status_data, dict) else None
        answer = (
            "I can explain why a token has attention, summarize KOL sentiment, rank KOL track records, "
            "rank risky tokens, screen tokens by liquidity/risk/KOL/smart-money criteria, inspect smart-money activity, "
            "and compare tracked tokens. "
            f"The backend is currently in {data_mode or 'unknown'} KOL mode with "
            f"{int((record_counts or {}).get('tokens') or 0)} tracked tokens."
        )
        evidence = [self._data_mode_evidence(status_result)]
        missing_data = [] if record_counts else ["backend_data_status"]
        return self._result_payload(
            answer=answer,
            evidence_used=[item for item in evidence if item is not None],
            missing_data=missing_data,
            tool_calls=tool_calls,
        )

    def _run_tool_plan(self, plan: list[ToolPlanStep]) -> list[ToolCallRecord]:
        if not plan:
            return []

        async def runner() -> list[ToolCallRecord]:
            return await asyncio.gather(
                *(self._invoke_tool(step) for step in plan),
            )

        return asyncio.run(runner())

    async def _invoke_tool(self, step: ToolPlanStep) -> ToolCallRecord:
        started_at = time.perf_counter()
        try:
            result = await self.registry.call_tool(step.tool_name, step.input_args)
        except Exception as exc:
            result = AgentToolResult(
                skill_name="tool_registry",
                tool_name=step.tool_name,
                input_args=step.input_args,
                source="tool_registry",
                status="error",
                latency_ms=self._latency_ms(started_at),
                fetched_at=self._now(),
                data=None,
                error=str(exc),
            )
        return ToolCallRecord(
            alias=step.alias,
            tool_name=step.tool_name,
            input_args=step.input_args,
            result=result,
        )

    def _classify_intent(
        self,
        message: str,
        *,
        token_context: dict[str, Any] | None,
    ) -> ChatIntent:
        lowered = message.lower()
        extracted_identifiers = self._extract_token_strings(message)
        extracted_handles = self._extract_handles(message)
        has_identifiers = bool(
            token_context
            or extracted_identifiers["addresses"]
            or extracted_identifiers["symbols"]
        )
        identifier_count = len(extracted_identifiers["addresses"]) + len(extracted_identifiers["symbols"])
        generic_trending_query = bool(
            re.search(r"\b(which|what)\b.*\btokens?\b.*\btrending\b", lowered)
        ) or bool(
            re.search(r"\btrending\b.*\btokens?\b", lowered)
        )

        if (
            (" vs " in lowered or " versus " in lowered or "compare" in lowered)
            and identifier_count >= 2
        ):
            return "compare_tokens"

        screening_signal_count = sum(
            1
            for marker in (
                "liquidity",
                "audit risk",
                "low risk",
                "low audit risk",
                "smart money",
                "smart-money",
                "kol sentiment",
                "positive kol",
                "positive sentiment",
            )
            if marker in lowered
        )
        if (
            any(
                phrase in lowered
                for phrase in (
                    "which ones have",
                    "rank the top",
                    "rank them",
                    "top 3",
                    "top three",
                    "tradeoffs",
                    "among the tokens",
                )
            )
            and screening_signal_count >= 2
        ):
            return "token_screening"

        if (
            any(
                phrase in lowered
                for phrase in (
                    "how do you calculate kol",
                    "how do you calculate the kol",
                    "how are kol rankings",
                    "kol ranking methodology",
                    "how do you calculate historical alignment",
                    "how are track record scores",
                    "methodology",
                )
            )
            and any(
                term in lowered
                for term in ("kol", "track record", "historical alignment", "rankings", "score")
            )
        ):
            return "kol_performance_methodology"

        if (
            any(
                phrase in lowered
                for phrase in (
                    "examples of kol calls",
                    "show me examples",
                    "were right or wrong",
                    "were right",
                    "were wrong",
                )
            )
            and any(term in lowered for term in ("kol", "calls", "track record", "historical alignment"))
        ):
            return "kol_call_examples"

        if any(
            phrase in lowered
            for phrase in (
                "which kols have the best track record",
                "rank the kols",
                "rank kols",
                "kol rankings",
                "best track record",
                "weak historical alignment",
                "historically bad",
                "lowest score",
                "which kols have weak historical alignment",
                "top kols",
                "best kols",
            )
        ):
            return "kol_rankings"

        if any(
            phrase in lowered
            for phrase in (
                "track record",
                "historical alignment",
                "how has this kol performed",
                "how has this handle performed",
                "why does this kol have a low score",
                "why does this handle have a low score",
                "why does @",
                "low score",
                "performed",
            )
        ) and (bool(extracted_handles) or "this kol" in lowered or "this handle" in lowered):
            return "kol_track_record"

        if any(keyword in lowered for keyword in ("risk", "risky", "unsafe", "danger")):
            return "high_risk_tokens"

        if any(keyword in lowered for keyword in ("smart money", "smart-money", "inflow", "whale")):
            return "smart_money_activity"

        if any(keyword in lowered for keyword in ("kol", "sentiment", "mentioned", "twitter", "social", "handle")) and not any(
            keyword in lowered for keyword in ("backed by market", "supported by market", "hype backed", "hype supported")
        ):
            return "kol_sentiment"

        if any(
            keyword in lowered
            for keyword in (
                "why is",
                "why this",
                "explain",
                "attention",
                "backed by market",
                "supported by market",
                "hype backed",
                "hype supported",
            )
        ):
            return "token_explanation"

        if "trending" in lowered or "top tokens" in lowered or "current signals" in lowered:
            if generic_trending_query and not token_context and not extracted_identifiers["addresses"]:
                return "trending_tokens"
            return "token_explanation" if has_identifiers else "trending_tokens"

        if has_identifiers:
            return "token_explanation"

        if any(keyword in lowered for keyword in ("help", "what can you do", "how do you work")):
            return "general_help"

        return "trending_tokens"

    def _resolve_tokens(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
        max_tokens: int,
        allow_fallback: bool,
    ) -> TokenResolution:
        resolved: list[ResolvedToken] = []
        ambiguous_symbols: list[str] = []
        seen_keys: set[tuple[str, str]] = set()

        def add_token(token: ResolvedToken) -> None:
            key = (token.chain_id, token.contract_address)
            if key in seen_keys or len(resolved) >= max_tokens:
                return
            seen_keys.add(key)
            resolved.append(token)

        explicit = self._resolve_from_token_context(token_context, chain_id=chain_id)
        for token in explicit.tokens:
            add_token(token)
        ambiguous_symbols.extend(explicit.ambiguous_symbols)

        identifiers = self._extract_token_strings(message)
        for address in identifiers["addresses"]:
            token = self._lookup_token_by_contract(address, chain_id=chain_id)
            if token is not None:
                add_token(token)

        for symbol in identifiers["symbols"]:
            matches = self._lookup_tokens_by_symbol(symbol, chain_id=chain_id)
            if len(matches) == 1:
                add_token(matches[0])
            elif len(matches) > 1:
                selected = self._select_best_resolved_token(matches)
                if selected is not None:
                    add_token(selected)
                elif symbol not in ambiguous_symbols:
                    ambiguous_symbols.append(symbol)

        warning: str | None = explicit.warning
        if not resolved and allow_fallback:
            inferred_tokens, inferred_warning, inferred_ambiguous = self._infer_tokens_from_message(
                message=message,
                chain_id=chain_id,
                max_tokens=max_tokens,
            )
            for token in inferred_tokens:
                add_token(token)
            for symbol in inferred_ambiguous:
                if symbol not in ambiguous_symbols:
                    ambiguous_symbols.append(symbol)
            if inferred_warning:
                warning = inferred_warning

        return TokenResolution(
            tokens=tuple(resolved),
            ambiguous_symbols=tuple(ambiguous_symbols),
            warning=warning,
        )

    def _infer_chain_id_from_message(self, message: str) -> str | None:
        lowered = message.lower()
        if "solana" in lowered or re.search(r"\bsol\b", lowered):
            return "CT_501"
        if "bnb chain" in lowered or "binance smart chain" in lowered or re.search(r"\bbsc\b", lowered):
            return "56"
        if re.search(r"\bon base\b", lowered) or "base chain" in lowered:
            return "8453"
        return None

    def _resolve_from_token_context(
        self,
        token_context: dict[str, Any] | None,
        *,
        chain_id: str | None,
    ) -> TokenResolution:
        if not token_context:
            return TokenResolution(tokens=(), ambiguous_symbols=(), warning=None)

        context_chain_id = self._context_string(token_context.get("chain_id")) or chain_id
        contract_address = self._context_string(token_context.get("contract_address"))
        symbol = self._context_string(token_context.get("symbol"))
        name = self._context_string(token_context.get("name"))

        if contract_address:
            token = self._lookup_token_by_contract(contract_address, chain_id=context_chain_id)
            if token is not None:
                return TokenResolution(tokens=(token,), ambiguous_symbols=(), warning=None)

        if symbol:
            matches = self._lookup_tokens_by_symbol(symbol, chain_id=context_chain_id)
            if len(matches) == 1:
                return TokenResolution(tokens=(matches[0],), ambiguous_symbols=(), warning=None)
            if len(matches) > 1:
                return TokenResolution(tokens=(), ambiguous_symbols=(symbol.upper(),), warning=None)

        if name:
            matches = self._lookup_tokens_by_name(name, chain_id=context_chain_id)
            if len(matches) == 1:
                return TokenResolution(tokens=(matches[0],), ambiguous_symbols=(), warning=None)

        return TokenResolution(tokens=(), ambiguous_symbols=(), warning=None)

    def _lookup_token_by_contract(
        self,
        contract_address: str,
        *,
        chain_id: str | None,
    ) -> ResolvedToken | None:
        normalized_contract = contract_address.strip().lower()
        statement = select(Token).where(func.lower(Token.contract_address) == normalized_contract)
        if chain_id:
            statement = statement.where(Token.chain_id == chain_id)
        tokens = self.db.execute(statement.order_by(desc(Token.updated_at)).limit(5)).scalars().all()
        if len(tokens) != 1:
            if not tokens:
                return None
            return self._to_resolved_token(tokens[0])
        return self._to_resolved_token(tokens[0])

    def _lookup_tokens_by_symbol(
        self,
        symbol: str,
        *,
        chain_id: str | None,
    ) -> list[ResolvedToken]:
        normalized_symbol = symbol.strip().upper()
        statement = select(Token).where(func.upper(Token.symbol) == normalized_symbol)
        if chain_id:
            statement = statement.where(Token.chain_id == chain_id)
        tokens = self.db.execute(statement.order_by(desc(Token.updated_at)).limit(10)).scalars().all()
        return [self._to_resolved_token(token) for token in tokens]

    def _lookup_tokens_by_name(
        self,
        name: str,
        *,
        chain_id: str | None,
    ) -> list[ResolvedToken]:
        lowered_name = name.strip().lower()
        statement = select(Token).where(func.lower(func.coalesce(Token.name, "")) == lowered_name)
        if chain_id:
            statement = statement.where(Token.chain_id == chain_id)
        tokens = self.db.execute(statement.order_by(desc(Token.updated_at)).limit(10)).scalars().all()
        return [self._to_resolved_token(token) for token in tokens]

    def _select_best_resolved_token(
        self,
        candidates: list[ResolvedToken],
    ) -> ResolvedToken | None:
        ranked = sorted(
            candidates,
            key=lambda token: (
                float(token.attention_score or 0.0),
                token.chain_id == self._default_chain_id(),
            ),
            reverse=True,
        )
        if not ranked:
            return None
        if len(ranked) == 1:
            return ranked[0]

        top = ranked[0]
        runner_up = ranked[1]
        top_score = float(top.attention_score or 0.0)
        runner_up_score = float(runner_up.attention_score or 0.0)

        if top_score <= 0.0 and runner_up_score <= 0.0:
            return None
        if top_score - runner_up_score >= 10.0:
            return top
        if top_score > 0.0 and runner_up_score == 0.0:
            return top
        return None

    def _infer_tokens_from_message(
        self,
        *,
        message: str,
        chain_id: str | None,
        max_tokens: int,
    ) -> tuple[list[ResolvedToken], str | None, list[str]]:
        lowered = message.lower()
        query_terms = self._token_query_terms(message)
        alias_targets = self._alias_targets(lowered)

        if not query_terms and not alias_targets:
            return [], None, []

        statement = select(Token)
        if chain_id:
            statement = statement.where(Token.chain_id == chain_id)
        candidates = self.db.execute(
            statement.order_by(desc(Token.updated_at)).limit(250)
        ).scalars().all()

        scored: list[tuple[float, ResolvedToken, list[str]]] = []
        for token in candidates:
            resolved = self._to_resolved_token(token)
            score, reasons = self._score_token_candidate(
                resolved,
                lowered_message=lowered,
                query_terms=query_terms,
                alias_targets=alias_targets,
            )
            if score > 0.0:
                scored.append((score, resolved, reasons))

        scored.sort(
            key=lambda item: (
                item[0],
                float(item[1].attention_score or 0.0),
                item[1].chain_id == self._default_chain_id(),
            ),
            reverse=True,
        )

        if not scored:
            return [], None, []

        top_score, top_token, reasons = scored[0]
        if top_score < 4.0:
            return [], None, []

        if len(scored) > 1:
            runner_up_score, runner_up_token, _ = scored[1]
            close_match = (top_score - runner_up_score) < 2.0
            if close_match:
                return [], None, [
                    label
                    for label in (
                        top_token.symbol or top_token.name or top_token.contract_address,
                        runner_up_token.symbol or runner_up_token.name or runner_up_token.contract_address,
                    )
                    if label
                ]

        reason_text = ", ".join(reasons[:2]) if reasons else "plain-English token matching"
        warning = (
            f"I inferred you likely meant {self._token_label(top_token)} based on {reason_text}."
        )
        return [top_token][:max_tokens], warning, []

    def _token_query_terms(self, message: str) -> list[str]:
        words = re.findall(r"[A-Za-z0-9]{2,}", message.lower())
        terms: list[str] = []
        for word in words:
            if word in TOKEN_QUERY_STOPWORDS:
                continue
            if len(word) <= 2:
                continue
            if word not in terms:
                terms.append(word)

        bigrams = [
            f"{left} {right}"
            for left, right in zip(terms, terms[1:])
            if left not in TOKEN_QUERY_STOPWORDS and right not in TOKEN_QUERY_STOPWORDS
        ]
        for phrase in bigrams:
            if phrase not in terms:
                terms.append(phrase)
        return terms

    def _alias_targets(self, lowered_message: str) -> list[str]:
        targets: list[str] = []
        for phrase, aliases in TOKEN_ALIAS_HINTS.items():
            if phrase in lowered_message:
                for alias in aliases:
                    lowered_alias = alias.lower()
                    if lowered_alias not in targets:
                        targets.append(lowered_alias)
        return targets

    def _score_token_candidate(
        self,
        token: ResolvedToken,
        *,
        lowered_message: str,
        query_terms: list[str],
        alias_targets: list[str],
    ) -> tuple[float, list[str]]:
        normalized_symbol = (token.symbol or "").strip().lower()
        normalized_name = (token.name or "").strip().lower()
        if not normalized_symbol and not normalized_name:
            return 0.0, []

        score = 0.0
        reasons: list[str] = []
        name_terms = {
            term
            for term in re.findall(r"[a-z0-9]{2,}", normalized_name)
            if term not in TOKEN_QUERY_STOPWORDS
        }

        if normalized_symbol and re.search(rf"\b{re.escape(normalized_symbol)}\b", lowered_message):
            score += 10.0
            reasons.append(f"symbol match '{token.symbol}'")

        if normalized_name and normalized_name in lowered_message:
            score += 12.0
            reasons.append(f"name match '{token.name}'")

        for alias in alias_targets:
            if alias == normalized_symbol or (normalized_name and alias in normalized_name):
                score += 9.0
                reasons.append(f"alias match '{alias}'")

        overlapping_terms = [
            term
            for term in query_terms
            if term == normalized_symbol or term in name_terms
        ]
        if overlapping_terms:
            score += 4.0 * len(overlapping_terms)
            for term in overlapping_terms[:2]:
                reasons.append(f"term match '{term}'")

        partial_terms = [
            term
            for term in query_terms
            if len(term) >= 4
            and term not in overlapping_terms
            and (
                (normalized_symbol and term in normalized_symbol)
                or (normalized_name and term in normalized_name)
            )
        ]
        if partial_terms:
            score += 1.5 * len(partial_terms)
            for term in partial_terms[:2]:
                reasons.append(f"partial match '{term}'")

        fuzzy_terms = []
        for term in query_terms:
            if len(term) < 4 or term in overlapping_terms or term in partial_terms:
                continue
            similarity_to_symbol = (
                SequenceMatcher(None, term, normalized_symbol).ratio()
                if normalized_symbol
                else 0.0
            )
            similarity_to_name = max(
                (SequenceMatcher(None, term, name_term).ratio() for name_term in name_terms),
                default=0.0,
            )
            if max(similarity_to_symbol, similarity_to_name) >= 0.79:
                fuzzy_terms.append(term)

        if fuzzy_terms:
            score += 2.5 * len(fuzzy_terms)
            for term in fuzzy_terms[:2]:
                reasons.append(f"fuzzy match '{term}'")

        if any(flag in lowered_message for flag in ("meme coin", "memecoin", "meme")) and self._looks_meme_like(token):
            score += 1.0
            reasons.append("meme-token context")

        if token.attention_score is not None:
            score += min(float(token.attention_score) / 100.0, 0.75)

        deduped_reasons = list(dict.fromkeys(reasons))
        return score, deduped_reasons

    def _looks_meme_like(self, token: ResolvedToken) -> bool:
        probe = f"{token.symbol or ''} {token.name or ''}".lower()
        return any(
            marker in probe
            for marker in (
                "pepe",
                "doge",
                "bonk",
                "wif",
                "dogwifhat",
                "floki",
                "trump",
                "melania",
                "inu",
            )
        )

    def _top_attention_token(self, *, chain_id: str | None) -> ResolvedToken | None:
        insight_statement = select(TokenInsight).order_by(desc(TokenInsight.final_score), desc(TokenInsight.ts))
        if chain_id:
            insight_statement = insight_statement.where(TokenInsight.chain_id == chain_id)
        top_insight = self.db.execute(insight_statement.limit(1)).scalar_one_or_none()
        if top_insight is not None:
            token = self.db.get(Token, (top_insight.chain_id, top_insight.contract_address))
            if token is not None:
                return self._to_resolved_token(token, attention_score=top_insight.final_score)

        token_statement = select(Token)
        if chain_id:
            token_statement = token_statement.where(Token.chain_id == chain_id)
        token = self.db.execute(token_statement.order_by(desc(Token.updated_at)).limit(1)).scalar_one_or_none()
        if token is None:
            return None
        return self._to_resolved_token(token)

    def _to_resolved_token(
        self,
        token: Token,
        *,
        attention_score: float | None = None,
    ) -> ResolvedToken:
        chain_meta = build_chain_option(token.chain_id)
        score = attention_score
        if score is None:
            insight = self.db.execute(
                select(TokenInsight)
                .where(
                    TokenInsight.chain_id == token.chain_id,
                    TokenInsight.contract_address == token.contract_address,
                )
                .order_by(desc(TokenInsight.ts))
                .limit(1)
            ).scalar_one_or_none()
            score = insight.final_score if insight else None
        return ResolvedToken(
            chain_id=token.chain_id,
            contract_address=token.contract_address,
            symbol=token.symbol,
            name=token.name,
            chain_name=chain_meta["name"],
            chain_short_name=chain_meta["short_name"],
            attention_score=score,
        )

    def _extract_token_strings(self, message: str) -> dict[str, list[str]]:
        addresses = list(dict.fromkeys(match.group(0) for match in EVM_ADDRESS_PATTERN.finditer(message)))
        cashtags = list(dict.fromkeys(match.group(1).upper() for match in CASHTAG_PATTERN.finditer(message)))
        symbols = list(cashtags)

        for match in WORD_PATTERN.finditer(message):
            candidate = match.group(0).strip()
            upper_candidate = candidate.upper()
            lowered = candidate.lower()
            if lowered in TOKEN_STOPWORDS:
                continue
            if upper_candidate not in symbols and (candidate.isupper() or len(candidate) <= 6):
                symbols.append(upper_candidate)

        return {
            "addresses": addresses,
            "symbols": symbols,
        }

    def _extract_handles(self, message: str) -> list[str]:
        return list(dict.fromkeys(match.group(1).lower() for match in HANDLE_PATTERN.finditer(message)))

    def _asks_for_generic_market_support(self, message: str) -> bool:
        lowered = message.lower()
        return any(
            phrase in lowered
            for phrase in (
                "backed by market",
                "supported by market",
                "hype backed",
                "hype supported",
            )
        )

    def _result_for_alias(
        self,
        tool_calls: list[ToolCallRecord],
        alias: str,
    ) -> AgentToolResult | None:
        for record in tool_calls:
            if record.alias == alias:
                return record.result
        return None

    def _result_payload(
        self,
        *,
        answer: str,
        evidence_used: list[dict[str, Any]],
        missing_data: list[str],
        tool_calls: list[ToolCallRecord],
    ) -> dict[str, Any]:
        return {
            "answer": answer,
            "evidence_used": evidence_used,
            "missing_data": list(dict.fromkeys(missing_data)),
            "tool_calls": tool_calls,
        }

    def _response(
        self,
        *,
        answer: str,
        evidence_used: list[dict[str, Any]],
        missing_data: list[str],
        tool_calls: list[ToolCallRecord],
        debug: bool,
    ) -> dict[str, Any]:
        full_trace = self._full_tool_trace(tool_calls)
        return {
            "answer": answer,
            "evidence_used": evidence_used,
            "missing_data": list(dict.fromkeys(missing_data)),
            "tool_trace": full_trace if debug else [self._compact_tool_trace_entry(entry) for entry in full_trace],
            "disclaimer": CHAT_DISCLAIMER,
        }

    def _full_tool_trace(self, tool_calls: list[ToolCallRecord]) -> list[dict[str, Any]]:
        trace: list[dict[str, Any]] = []
        for record in tool_calls:
            entry = record.result.model_dump(mode="json")
            entry["registry_name"] = record.tool_name
            if record.alias != record.tool_name:
                entry["call_alias"] = record.alias
            trace.append(entry)
        return trace

    def _compact_tool_trace_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        compact = {
            "tool_name": entry.get("tool_name"),
            "registry_name": entry.get("registry_name"),
            "source": entry.get("source"),
            "status": entry.get("status"),
            "latency_ms": entry.get("latency_ms"),
            "fetched_at": entry.get("fetched_at"),
        }
        if entry.get("call_alias"):
            compact["call_alias"] = entry.get("call_alias")
        if entry.get("error"):
            compact["error"] = entry.get("error")
        return compact

    def _derive_run_status(
        self,
        tool_calls: list[ToolCallRecord],
        missing_data: list[str],
    ) -> str:
        statuses = {record.result.status for record in tool_calls}
        if statuses and statuses == {"error"}:
            return "error"
        if "error" in statuses or missing_data:
            return "partial"
        return "ok"

    def _store_logs(
        self,
        *,
        request_id: str,
        message: str,
        normalized_intent: str,
        response: dict[str, Any],
        full_tool_trace: list[dict[str, Any]],
        total_latency_ms: int,
        status: str,
    ) -> None:
        evidence_json = json.dumps(response.get("evidence_used", []), default=str, separators=(",", ":"))
        missing_data_json = json.dumps(response.get("missing_data", []), default=str, separators=(",", ":"))
        tool_trace_json = json.dumps(full_tool_trace, default=str, separators=(",", ":"))
        settings = get_settings()

        agent_run = AgentRun(
            request_id=request_id,
            user_message=message,
            normalized_intent=normalized_intent,
            answer=str(response.get("answer") or ""),
            evidence_json=evidence_json,
            missing_data_json=missing_data_json,
            tool_trace_json=tool_trace_json,
            data_mode=settings.kol_data_mode,
            total_latency_ms=total_latency_ms,
            status=status,
        )
        chat_log = ChatLog(
            user_message=message,
            assistant_answer=str(response.get("answer") or ""),
            tool_calls_json=tool_trace_json,
            evidence_json=json.dumps(
                {
                    "evidence_used": response.get("evidence_used", []),
                    "missing_data": response.get("missing_data", []),
                    "normalized_intent": normalized_intent,
                    "request_id": request_id,
                    "status": status,
                },
                default=str,
                separators=(",", ":"),
            ),
        )
        try:
            self.db.add(agent_run)
            self.db.add(chat_log)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _ambiguous_token_payload(self, resolution: TokenResolution) -> dict[str, Any]:
        candidates = ", ".join(resolution.ambiguous_symbols[:3]) or "that symbol"
        return self._result_payload(
            answer=f"I found multiple stored matches for {candidates}. Please specify the chain or contract address.",
            evidence_used=[],
            missing_data=["specific_token"],
            tool_calls=[],
        )

    def _sorted_local_trending_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            items,
            key=lambda item: (
                float(item.get("attention_score") or 0.0),
                int(item.get("smart_money_signal_count") or 0),
                int(item.get("kol_mention_count") or 0),
                float(item.get("volume_24h") or 0.0),
            ),
            reverse=True,
        )

    def _format_item_list(self, items: list[dict[str, Any]]) -> str:
        labels = [self._item_label(item) for item in items if self._item_label(item)]
        return self._format_list(labels)

    def _format_live_rank_list(self, items: list[dict[str, Any]]) -> str:
        labels = []
        for item in items:
            symbol = item.get("symbol") or item.get("ticker") or item.get("tokenSymbol")
            contract = item.get("contractAddress") or item.get("ca")
            label = str(symbol or contract or "unknown token")
            labels.append(label)
        return self._format_list(labels)

    def _item_label(self, item: dict[str, Any]) -> str:
        symbol = item.get("symbol") or item.get("token_symbol")
        name = item.get("token_name") or item.get("name")
        chain_short_name = item.get("chain_short_name")
        contract = item.get("contract_address") or item.get("contractAddress")
        base_label = self._composed_token_label(
            symbol=symbol,
            name=name,
            contract_address=contract,
            include_chain=False,
            chain_short_name=chain_short_name,
        )
        if chain_short_name and base_label:
            return f"{base_label} on {chain_short_name}"
        if base_label:
            return str(base_label)
        return str(contract or "")

    def _format_list(self, items: list[str]) -> str:
        items = [item for item in items if item]
        if not items:
            return "no matching items"
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return f"{', '.join(items[:-1])}, and {items[-1]}"

    def _screening_requested_criteria(self, message: str) -> list[str]:
        lowered = message.lower()
        criteria: list[str] = []
        if any(marker in lowered for marker in ("positive kol", "kol sentiment", "positive sentiment")):
            criteria.append("positive_kol")
        if "liquidity" in lowered or "liquid" in lowered:
            criteria.append("decent_liquidity")
        if any(marker in lowered for marker in ("low audit risk", "low risk", "safer", "safe")):
            criteria.append("low_risk")
        if any(marker in lowered for marker in ("smart money", "smart-money", "whale", "inflow")):
            criteria.append("smart_money_support")
        return criteria

    def _screening_analysis(self, item: dict[str, Any]) -> dict[str, Any]:
        liquidity = self._to_float(item.get("liquidity"))
        attention_score = self._to_float(item.get("attention_score"))
        safety_score = self._to_float(item.get("safety_score"))
        risk_level = self._normalize_key(item.get("risk_level_enum"))
        bullish_mentions = int(item.get("bullish_mentions") or 0)
        bearish_mentions = int(item.get("bearish_mentions") or 0)
        mention_count = int(item.get("kol_mention_count") or 0)
        positive_signals = int(item.get("positive_signal_count") or 0)
        signal_count = int(item.get("smart_money_signal_count") or 0)
        matched_criteria: list[str] = []
        tradeoffs: list[str] = []

        if mention_count > 0 and bullish_mentions > bearish_mentions:
            matched_criteria.append("positive KOL sentiment")
        elif mention_count == 0:
            tradeoffs.append("KOL coverage is still thin")
        else:
            tradeoffs.append("KOL sentiment is mixed")

        if liquidity is not None and liquidity >= 250_000.0:
            matched_criteria.append(f"{self._format_number(liquidity)} liquidity")
        else:
            tradeoffs.append("liquidity is still on the lighter side")

        if risk_level == "low" and (safety_score is None or safety_score >= 70.0):
            matched_criteria.append(
                f"low audit risk{'' if safety_score is None else f' and safety {safety_score:.0f}'}"
            )
        else:
            tradeoffs.append("risk readings are not especially light")

        if positive_signals > 0:
            matched_criteria.append(
                f"{positive_signals} positive smart-money signal{'' if positive_signals == 1 else 's'}"
            )
        elif signal_count > 0:
            tradeoffs.append("smart-money support is present but mixed")
        else:
            tradeoffs.append("smart-money support is muted")

        return {
            "item": item,
            "label": self._item_label(item),
            "attention_score": attention_score,
            "liquidity": liquidity,
            "matched_criteria": matched_criteria,
            "matched_criteria_count": len(matched_criteria),
            "tradeoffs": tradeoffs,
        }

    def _screening_score(self, *, item: dict[str, Any], analysis: dict[str, Any]) -> float:
        return (
            float(analysis.get("matched_criteria_count") or 0) * 25.0
            + float(item.get("attention_score") or 0.0) * 0.35
            + min(float(item.get("liquidity") or 0.0) / 500_000.0, 12.0)
            + min(int(item.get("positive_signal_count") or 0) * 4.0, 12.0)
        )

    def _screening_summary(self, analysis: dict[str, Any]) -> str:
        item = analysis["item"]
        matched_criteria = analysis.get("matched_criteria") or []
        tradeoffs = analysis.get("tradeoffs") or []
        attention_score = self._to_float(item.get("attention_score"))

        lead = (
            f"{analysis['label']} matches on {self._format_list(matched_criteria[:3])}"
            if matched_criteria
            else f"{analysis['label']} is still mostly an attention-led candidate"
        )
        if attention_score is not None:
            lead += f" with {ATTENTION_SCORE_NAME} {attention_score:.0f}"
        if tradeoffs:
            lead += f"; tradeoff: {tradeoffs[0]}"
        return lead + "."

    def _screening_evidence(
        self,
        *,
        chain_name: str,
        requested_criteria: list[str],
        shortlisted: list[dict[str, Any]],
        used_fallback: bool,
    ) -> dict[str, Any]:
        return {
            "type": "token_screening",
            "chain_name": chain_name,
            "requested_criteria": requested_criteria,
            "used_closest_matches": used_fallback,
            "items": [
                {
                    "token": analysis["label"],
                    "matched_criteria": analysis.get("matched_criteria", []),
                    "tradeoffs": analysis.get("tradeoffs", []),
                    "attention_score": analysis.get("attention_score"),
                }
                for analysis in shortlisted
            ],
        }

    def _sample_size_text(self, sample_size_confidence: float) -> str:
        if sample_size_confidence >= 1.0:
            return "the sample is reasonably established"
        if sample_size_confidence >= 0.6:
            return "the sample is informative but still moderate"
        if sample_size_confidence > 0.0:
            return "the sample is still small and should be read cautiously"
        return "there is not enough evaluated history yet"

    def _format_kol_call_examples(self, items: list[dict[str, Any]]) -> str:
        labels: list[str] = []
        for item in items:
            handle = item.get("handle")
            direction = item.get("direction")
            token_symbol = item.get("token_symbol") or item.get("symbol_text") or item.get("contract_address")
            window = item.get("primary_window") or "24h"
            primary_return = self._to_float(item.get("primary_return"))
            if handle and direction and token_symbol and primary_return is not None:
                outcome = "hit" if item.get("is_hit") is True else "miss"
                labels.append(
                    f"@{handle} {direction} on {token_symbol} "
                    f"({outcome}, {window} return {primary_return * 100:.1f}%)"
                )
        return self._format_list(labels) if labels else ""

    def _token_label(self, token: ResolvedToken) -> str:
        return self._composed_token_label(
            symbol=token.symbol,
            name=token.name,
            contract_address=token.contract_address,
            include_chain=True,
            chain_short_name=token.chain_short_name,
        )

    def _token_base_label(self, token: ResolvedToken) -> str:
        return self._composed_token_label(
            symbol=token.symbol,
            name=token.name,
            contract_address=token.contract_address,
            include_chain=False,
            chain_short_name=token.chain_short_name,
        )

    def _composed_token_label(
        self,
        *,
        symbol: Any,
        name: Any,
        contract_address: Any,
        include_chain: bool,
        chain_short_name: str | None,
    ) -> str:
        normalized_symbol = self._context_string(symbol) or ""
        normalized_name = self._context_string(name) or ""
        normalized_contract = self._context_string(contract_address) or ""

        if normalized_name and normalized_symbol and normalized_name.casefold() != normalized_symbol.casefold():
            base_label = f"{normalized_name} ({normalized_symbol})"
        else:
            base_label = normalized_symbol or normalized_name or normalized_contract

        if include_chain and chain_short_name:
            return f"{base_label} on {chain_short_name}"
        return base_label

    def _present_insight_summary(
        self,
        token: ResolvedToken,
        insight: dict[str, Any],
    ) -> str:
        summary = self._context_string(insight.get("summary"))
        if not summary:
            return f"{self._token_label(token)} is in the local dataset, but I do not have a stored insight summary for it yet."

        display_label = self._token_label(token)
        replacement_candidates = [
            self._token_base_label(token),
            self._context_string(token.symbol),
            self._context_string(token.name),
            self._context_string(token.contract_address),
        ]

        for candidate in replacement_candidates:
            if not candidate:
                continue
            pattern = re.compile(rf"^{re.escape(candidate)}\b", re.IGNORECASE)
            if pattern.search(summary):
                return pattern.sub(display_label, summary, count=1)

        if display_label.casefold() in summary.casefold():
            return summary
        return f"{display_label}: {summary}"

    def _tool_dict(self, result: AgentToolResult | None) -> dict[str, Any]:
        if result is None or not isinstance(result.data, dict):
            return {}
        return result.data

    def _tool_items(self, result: AgentToolResult | None) -> list[dict[str, Any]]:
        data = self._tool_dict(result)
        items = data.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []

    def _tool_nested_dict(self, result: AgentToolResult | None, key: str) -> dict[str, Any]:
        data = self._tool_dict(result)
        nested = data.get(key)
        return nested if isinstance(nested, dict) else {}

    def _tool_dynamic_market_data(self, result: AgentToolResult | None) -> dict[str, Any]:
        data = self._tool_dict(result)
        dynamic = data.get("dynamic_market_data")
        return dynamic if isinstance(dynamic, dict) else {}

    def _derived_query_text(self, message: str, token: ResolvedToken | None) -> str | None:
        if token is not None:
            return token.symbol or token.name or token.contract_address
        handles = self._extract_handles(message)
        if handles:
            return handles[0]
        cashtags = [match.group(1).upper() for match in CASHTAG_PATTERN.finditer(message)]
        if cashtags:
            return cashtags[0]
        words = self._extract_token_strings(message)["symbols"]
        return words[0] if words else None

    def _asks_for_handles(self, message: str) -> bool:
        lowered = message.lower()
        return "which kols" in lowered or "who mentioned" in lowered or "which handles" in lowered

    def _handle_specific_kol_answer(
        self,
        *,
        handle: str,
        profile: dict[str, Any],
        stats: dict[str, Any],
        mention_items: list[dict[str, Any]],
    ) -> str:
        if not profile:
            return f"I do not have a stored profile for @{handle}."

        answer = (
            f"@{handle} is in the local KOL dataset as {profile.get('display_name') or handle}. "
            f"They have {int(stats.get('post_count') or 0)} stored post"
            f"{'' if int(stats.get('post_count') or 0) == 1 else 's'}, "
            f"{int(stats.get('bullish_posts') or 0)} bullish, "
            f"{int(stats.get('bearish_posts') or 0)} bearish, "
            f"and {int(stats.get('resolved_mention_count') or 0)} resolved token mention"
            f"{'' if int(stats.get('resolved_mention_count') or 0) == 1 else 's'}."
        )
        if mention_items:
            grouped_tokens = self._group_mentions_by_token(mention_items)
            if grouped_tokens:
                answer += f" Their recent token focus includes {self._format_token_groups(list(grouped_tokens.values())[:3])}."
        return answer

    def _group_mentions_by_handle(self, mention_items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in mention_items:
            handle = str(item.get("handle") or "")
            if not handle:
                continue
            entry = grouped.setdefault(
                handle,
                {
                    "handle": handle,
                    "display_name": item.get("display_name"),
                    "mentions": 0,
                    "bullish": 0,
                    "bearish": 0,
                },
            )
            entry["mentions"] += 1
            sentiment = str(item.get("sentiment") or "").lower()
            if sentiment == "bullish":
                entry["bullish"] += 1
            elif sentiment == "bearish":
                entry["bearish"] += 1
        return dict(
            sorted(
                grouped.items(),
                key=lambda row: (
                    row[1]["mentions"],
                    row[1]["bullish"] - row[1]["bearish"],
                ),
                reverse=True,
            )
        )

    def _group_mentions_by_token(self, mention_items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in mention_items:
            key = (
                f"{item.get('chain_id') or 'unknown'}:"
                f"{item.get('contract_address') or item.get('symbol_text') or item.get('token_symbol') or 'unknown'}"
            )
            label = self._item_label(
                {
                    "symbol": item.get("token_symbol") or item.get("symbol_text"),
                    "chain_short_name": build_chain_option(item.get("chain_id") or "unknown")["short_name"]
                    if item.get("chain_id")
                    else None,
                    "contract_address": item.get("contract_address"),
                }
            )
            entry = grouped.setdefault(
                key,
                {
                    "label": label,
                    "mentions": 0,
                    "bullish": 0,
                    "bearish": 0,
                    "engagement": 0,
                },
            )
            entry["mentions"] += 1
            sentiment = str(item.get("sentiment") or "").lower()
            if sentiment == "bullish":
                entry["bullish"] += 1
            elif sentiment == "bearish":
                entry["bearish"] += 1
            engagement = item.get("engagement") or {}
            if isinstance(engagement, dict):
                entry["engagement"] += int(
                    (engagement.get("like_count") or 0)
                    + (engagement.get("repost_count") or 0)
                    + (engagement.get("reply_count") or 0)
                    + (engagement.get("view_count") or 0)
                )
        return dict(
            sorted(
                grouped.items(),
                key=lambda row: (
                    row[1]["bullish"] - row[1]["bearish"],
                    row[1]["mentions"],
                    row[1]["engagement"],
                ),
                reverse=True,
            )
        )

    def _format_handle_groups(self, groups: list[dict[str, Any]]) -> str:
        labels = [
            f"@{group['handle']} ({group['mentions']} mention{'s' if group['mentions'] != 1 else ''})"
            for group in groups
        ]
        return self._format_list(labels)

    def _format_token_groups(self, groups: list[dict[str, Any]]) -> str:
        labels = [
            f"{group['label']} ({group['bullish']} bullish, {group['bearish']} bearish)"
            for group in groups
            if group.get("label")
        ]
        return self._format_list(labels)

    def _mention_breakdown(self, mention_items: list[dict[str, Any]]) -> dict[str, int]:
        breakdown = defaultdict(int)
        breakdown["mention_count"] = 0
        breakdown["bullish"] = 0
        breakdown["bearish"] = 0
        breakdown["neutral"] = 0
        breakdown["unknown"] = 0
        for item in mention_items:
            breakdown["mention_count"] += 1
            sentiment = str(item.get("sentiment") or "").lower()
            if sentiment == "bullish":
                breakdown["bullish"] += 1
            elif sentiment == "bearish":
                breakdown["bearish"] += 1
            elif sentiment == "neutral":
                breakdown["neutral"] += 1
            else:
                breakdown["unknown"] += 1
        return dict(breakdown)

    def _token_mention_clause(
        self,
        token: ResolvedToken,
        mention_breakdown: dict[str, int],
    ) -> str | None:
        mention_count = int(mention_breakdown.get("mention_count") or 0)
        if mention_count == 0:
            return None
        bullish = int(mention_breakdown.get("bullish") or 0)
        bearish = int(mention_breakdown.get("bearish") or 0)
        return (
            f"Local KOL context shows {mention_count} mapped mention"
            f"{'' if mention_count == 1 else 's'} for {self._token_label(token)}, "
            f"with {bullish} bullish and {bearish} bearish."
        )

    def _market_clause(self, dynamic_market: dict[str, Any]) -> str | None:
        if not dynamic_market:
            return None
        percent_change = self._dynamic_number(
            dynamic_market,
            "percentChange24h",
            "priceChange24h",
        )
        volume = self._dynamic_number(dynamic_market, "volume24h", "volume")
        liquidity = self._dynamic_number(dynamic_market, "liquidity")

        fragments = []
        if percent_change is not None:
            fragments.append(f"24h change is {percent_change:.2f}%")
        if volume is not None:
            fragments.append(f"24h volume is {self._format_number(volume)}")
        if liquidity is not None:
            fragments.append(f"liquidity is {self._format_number(liquidity)}")
        if not fragments:
            return None
        return "Live market context says " + ", ".join(fragments) + "."

    def _risk_clause(
        self,
        audit_data: dict[str, Any],
        insight: dict[str, Any],
    ) -> str | None:
        fragments = []
        risk_level = self._normalize_key(
            audit_data.get("riskLevelEnum")
            or audit_data.get("risk_level_enum")
        )
        if risk_level:
            fragments.append(f"audit risk reads as {risk_level}")

        extra_info = audit_data.get("extraInfo")
        if isinstance(extra_info, dict):
            is_verified = self._to_bool(extra_info.get("isVerified"))
            if is_verified is False:
                fragments.append("contract verification is missing")
            buy_tax = self._percent(self._to_float(extra_info.get("buyTax")))
            sell_tax = self._percent(self._to_float(extra_info.get("sellTax")))
            if buy_tax is not None and buy_tax > 5.0:
                fragments.append(f"buy tax is {buy_tax:.1f}%")
            if sell_tax is not None and sell_tax > 5.0:
                fragments.append(f"sell tax is {sell_tax:.1f}%")

        if insight:
            safety_score = insight.get("safety_score")
            if safety_score is not None:
                fragments.append(f"safety score is {self._score_text(safety_score)}")

        if not fragments:
            return None
        return "Risk context: " + ", ".join(fragments[:3]) + "."

    def _specific_smart_money_answer(
        self,
        *,
        token: ResolvedToken,
        signal_data: dict[str, Any],
        smart_money_summary: dict[str, Any],
    ) -> str:
        live_signal_count = int(signal_data.get("signal_count") or 0)
        positive = int(signal_data.get("positive_count") or 0)
        negative = int(signal_data.get("negative_count") or 0)
        stored_signal_count = int(smart_money_summary.get("signal_count") or 0)
        if live_signal_count or stored_signal_count:
            return (
                f"Smart-money activity around {self._token_label(token)} shows "
                f"{live_signal_count} live signal{'s' if live_signal_count != 1 else ''} "
                f"({positive} positive, {negative} negative) and "
                f"{stored_signal_count} stored signal{'s' if stored_signal_count != 1 else ''}."
            )
        return f"I do not see meaningful smart-money activity for {self._token_label(token)} right now."

    def _comparison_answer(
        self,
        *,
        left: ResolvedToken,
        right: ResolvedToken,
        left_insight: dict[str, Any],
        right_insight: dict[str, Any],
        left_context: dict[str, Any],
        right_context: dict[str, Any],
    ) -> str:
        left_attention = self._to_float(left_insight.get("attention_score")) or 0.0
        right_attention = self._to_float(right_insight.get("attention_score")) or 0.0
        left_safety = self._to_float(left_insight.get("safety_score"))
        right_safety = self._to_float(right_insight.get("safety_score"))

        if left_attention > right_attention:
            lead = f"{self._token_label(left)} currently has the stronger {ATTENTION_SCORE_NAME}"
        elif right_attention > left_attention:
            lead = f"{self._token_label(right)} currently has the stronger {ATTENTION_SCORE_NAME}"
        else:
            lead = f"{self._token_label(left)} and {self._token_label(right)} currently look similar on {ATTENTION_SCORE_NAME}"

        comparison_bits = [
            f"{self._token_label(left)} is at {left_attention:.0f}",
            f"{self._token_label(right)} is at {right_attention:.0f}",
        ]

        if left_safety is not None and right_safety is not None:
            safer = left if left_safety > right_safety else right
            comparison_bits.append(
                f"{self._token_label(safer)} looks safer on the stored safety score"
            )

        left_mentions = self._context_mention_count(left_context)
        right_mentions = self._context_mention_count(right_context)
        if left_mentions or right_mentions:
            louder = left if left_mentions >= right_mentions else right
            comparison_bits.append(
                f"{self._token_label(louder)} has the stronger local KOL mention count"
            )

        return lead + ". " + ", while ".join(comparison_bits) + "."

    def _context_mention_count(self, context: dict[str, Any]) -> int:
        mention_summary = context.get("mention_summary")
        if isinstance(mention_summary, dict):
            return int(mention_summary.get("mention_count") or 0)
        return 0

    def _smart_money_missing_data(
        self,
        signal_data: dict[str, Any],
        smart_money_summary: dict[str, Any],
    ) -> list[str]:
        missing: list[str] = []
        if not signal_data:
            missing.append("live_smart_money_signals")
        if not smart_money_summary:
            missing.append("stored_smart_money_summary")
        return missing

    def _kol_missing_data(
        self,
        summary_result: AgentToolResult | None,
        mention_items: list[dict[str, Any]],
    ) -> list[str]:
        missing: list[str] = []
        if not mention_items:
            missing.append("kol_mentions")
        if summary_result is None or summary_result.status == "empty":
            missing.append("kol_profiles")
        return missing

    def _score_text(self, value: Any) -> str:
        numeric = self._to_float(value)
        return f"{numeric:.0f}" if numeric is not None else "unknown"

    def _specific_risk_evidence(
        self,
        item: dict[str, Any],
        result: AgentToolResult | None,
    ) -> dict[str, Any]:
        return {
            "type": "specific_risk_token",
            "status": result.status if result is not None else "unknown",
            "token": self._item_label(item),
            "risk_index": item.get("risk_index"),
            "safety_score": item.get("safety_score"),
            "risk_flags": item.get("risk_flags"),
        }

    def _risk_list_evidence(self, result: AgentToolResult | None) -> dict[str, Any] | None:
        items = self._tool_items(result)
        if not items:
            return None
        return {
            "type": "high_risk_token_list",
            "status": result.status if result is not None else "unknown",
            "count": len(items),
            "top_tokens": [self._item_label(item) for item in items[:5]],
        }

    def _local_trending_evidence(self, result: AgentToolResult | None) -> dict[str, Any] | None:
        items = self._sorted_local_trending_items(self._tool_items(result))
        if result is None:
            return None
        return {
            "type": "local_trending_context",
            "status": result.status,
            "count": len(items),
            "top_tokens": [self._item_label(item) for item in items[:5]],
            "data_mode": self._tool_dict(result).get("data_mode"),
        }

    def _live_rank_evidence(
        self,
        result: AgentToolResult | None,
        *,
        evidence_type: str,
    ) -> dict[str, Any] | None:
        if result is None:
            return None
        items = self._tool_items(result)
        return {
            "type": evidence_type,
            "status": result.status,
            "count": len(items),
            "top_symbols": [
                str(item.get("symbol") or item.get("ticker") or item.get("contractAddress") or "unknown")
                for item in items[:5]
            ],
        }

    def _insight_evidence(
        self,
        token: ResolvedToken,
        result: AgentToolResult | None,
    ) -> dict[str, Any] | None:
        insight = self._tool_nested_dict(result, "insight")
        if not insight:
            return None
        return {
            "type": "stored_insight",
            "token": self._token_label(token),
            "status": result.status if result is not None else "unknown",
            "attention_score": insight.get("attention_score"),
            "market_score": insight.get("market_score"),
            "kol_score": insight.get("kol_score"),
            "smart_money_score": insight.get("smart_money_score"),
            "safety_score": insight.get("safety_score"),
            "label": insight.get("label"),
        }

    def _kol_mention_evidence(
        self,
        token: ResolvedToken,
        mention_items: list[dict[str, Any]],
        result: AgentToolResult | None,
    ) -> dict[str, Any] | None:
        if not mention_items:
            return None
        breakdown = self._mention_breakdown(mention_items)
        handles = [item.get("handle") for item in mention_items[:5] if item.get("handle")]
        return {
            "type": "kol_mentions",
            "token": self._token_label(token),
            "status": result.status if result is not None else "unknown",
            "mention_count": breakdown.get("mention_count", 0),
            "bullish": breakdown.get("bullish", 0),
            "bearish": breakdown.get("bearish", 0),
            "handles": list(dict.fromkeys(handles)),
        }

    def _market_evidence(
        self,
        token: ResolvedToken,
        dynamic_market: dict[str, Any],
        result: AgentToolResult | None,
    ) -> dict[str, Any] | None:
        if not dynamic_market:
            return None
        return {
            "type": "live_market_data",
            "token": self._token_label(token),
            "status": result.status if result is not None else "unknown",
            "price": self._dynamic_number(dynamic_market, "price", "currentPrice"),
            "percent_change_24h": self._dynamic_number(dynamic_market, "percentChange24h", "priceChange24h"),
            "volume_24h": self._dynamic_number(dynamic_market, "volume24h", "volume"),
            "liquidity": self._dynamic_number(dynamic_market, "liquidity"),
        }

    def _audit_evidence(
        self,
        token: ResolvedToken,
        audit_data: dict[str, Any],
        insight: dict[str, Any],
        result: AgentToolResult | None,
    ) -> dict[str, Any] | None:
        if not audit_data and not insight:
            return None
        extra_info = audit_data.get("extraInfo")
        extra_info = extra_info if isinstance(extra_info, dict) else {}
        return {
            "type": "risk_context",
            "token": self._token_label(token),
            "status": result.status if result is not None else "unknown",
            "risk_level_enum": audit_data.get("riskLevelEnum") or audit_data.get("risk_level_enum"),
            "buy_tax": extra_info.get("buyTax"),
            "sell_tax": extra_info.get("sellTax"),
            "is_verified": extra_info.get("isVerified"),
            "safety_score": insight.get("safety_score") if insight else None,
        }

    def _kol_profile_evidence(self, result: AgentToolResult | None) -> dict[str, Any] | None:
        profile = self._tool_nested_dict(result, "profile")
        stats = self._tool_nested_dict(result, "stats")
        if not profile:
            return None
        return {
            "type": "kol_profile",
            "status": result.status if result is not None else "unknown",
            "handle": profile.get("handle"),
            "display_name": profile.get("display_name"),
            "category": profile.get("category"),
            "post_count": stats.get("post_count"),
            "resolved_mention_count": stats.get("resolved_mention_count"),
        }

    def _kol_search_evidence(
        self,
        result: AgentToolResult | None,
        mention_items: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if result is None:
            return None
        return {
            "type": "kol_search_results",
            "status": result.status,
            "match_count": len(mention_items),
            "handles": list(dict.fromkeys(item.get("handle") for item in mention_items if item.get("handle")))[:5],
        }

    def _kol_summary_list_evidence(self, result: AgentToolResult | None) -> dict[str, Any] | None:
        data = self._tool_dict(result)
        items = data.get("items")
        if not isinstance(items, list) or not items:
            return None
        return {
            "type": "kol_summary_list",
            "status": result.status if result is not None else "unknown",
            "count": len(items),
            "top_handles": [item.get("handle") for item in items[:5] if isinstance(item, dict)],
        }

    def _smart_money_signal_evidence(
        self,
        result: AgentToolResult | None,
        token: ResolvedToken,
    ) -> dict[str, Any] | None:
        if result is None:
            return None
        data = self._tool_dict(result)
        if not data:
            return None
        return {
            "type": "live_smart_money_signals",
            "token": self._token_label(token),
            "status": result.status,
            "signal_count": data.get("signal_count"),
            "positive_count": data.get("positive_count"),
            "negative_count": data.get("negative_count"),
        }

    def _stored_smart_money_evidence(
        self,
        result: AgentToolResult | None,
        token: ResolvedToken,
    ) -> dict[str, Any] | None:
        context = self._tool_dict(result)
        summary = context.get("smart_money_summary") if isinstance(context, dict) else None
        if not isinstance(summary, dict):
            return None
        return {
            "type": "stored_smart_money_summary",
            "token": self._token_label(token),
            "status": result.status if result is not None else "unknown",
            "signal_count": summary.get("signal_count"),
            "positive_signal_count": summary.get("positive_signal_count"),
            "negative_signal_count": summary.get("negative_signal_count"),
        }

    def _comparison_evidence(
        self,
        token: ResolvedToken,
        insight: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not insight and not context:
            return None
        mention_summary = context.get("mention_summary") if isinstance(context, dict) else {}
        latest_market = context.get("latest_market_snapshot") if isinstance(context, dict) else {}
        return {
            "type": "comparison_token",
            "token": self._token_label(token),
            "attention_score": insight.get("attention_score") if insight else None,
            "safety_score": insight.get("safety_score") if insight else None,
            "kol_score": insight.get("kol_score") if insight else None,
            "mention_count": mention_summary.get("mention_count") if isinstance(mention_summary, dict) else None,
            "percent_change_24h": latest_market.get("percent_change_24h") if isinstance(latest_market, dict) else None,
        }

    def _data_mode_evidence(self, result: AgentToolResult | None) -> dict[str, Any] | None:
        if result is None:
            return None
        data = self._tool_dict(result)
        record_counts = data.get("record_counts") if isinstance(data, dict) else None
        return {
            "type": "backend_data_status",
            "status": result.status,
            "kol_data_mode": data.get("kol_data_mode") if isinstance(data, dict) else None,
            "record_counts": record_counts if isinstance(record_counts, dict) else {},
        }

    def _format_risk_flags(self, flags: list[str]) -> str:
        if not flags:
            return "no specific risk flags"
        return self._format_list(flags[:3])

    def _dynamic_number(self, dynamic_market: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            if key in dynamic_market:
                value = self._to_float(dynamic_market.get(key))
                if value is not None:
                    return value
        return None

    def _default_chain_id(self) -> str:
        enabled = get_settings().enabled_chains
        return enabled[0] if enabled else "56"

    def _to_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_bool(self, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return None

    def _normalize_key(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _percent(self, value: Any) -> float | None:
        numeric = self._to_float(value)
        if numeric is None:
            return None
        if 0.0 <= abs(numeric) <= 1.0:
            return numeric * 100.0
        return numeric

    def _format_number(self, value: float) -> str:
        absolute = abs(value)
        if absolute >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if absolute >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if absolute >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:.2f}"

    def _context_string(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    def _latency_ms(self, started_at: float) -> int:
        return max(0, int(round((time.perf_counter() - started_at) * 1000)))

    def _now(self) -> datetime:
        return datetime.now(UTC)


__all__ = ["ChatAgentService"]
