from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.agent_tools.registry import RegisteredTool, ToolRegistry
from app.config import Settings, get_settings
from app.schemas import AgentToolResult
from app.services.chat_agent import ChatAgentService, ToolCallRecord

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - dependency is optional at runtime
    OpenAI = None


FORBIDDEN_LANGUAGE_PATTERNS = [
    re.compile(r"\byou should buy\b", re.IGNORECASE),
    re.compile(r"\byou should sell\b", re.IGNORECASE),
    re.compile(r"\bguaranteed profit\b", re.IGNORECASE),
    re.compile(r"\bguaranteed safe\b", re.IGNORECASE),
    re.compile(r"\brisk[- ]free\b", re.IGNORECASE),
    re.compile(r"\bthis will pump\b", re.IGNORECASE),
]


class OpenAIAgentService(ChatAgentService):
    MAX_TOOL_ROUNDS = 4

    def __init__(
        self,
        db: Session,
        *,
        registry: ToolRegistry | None = None,
        client: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(db, registry=registry)
        self.settings = settings or get_settings()
        self.client = client

    @classmethod
    def is_ready(cls, settings: Settings | None = None) -> bool:
        effective_settings = settings or get_settings()
        return OpenAI is not None and bool(effective_settings.openai_api_key)

    def answer_question(
        self,
        *,
        message: str,
        chain_id: str | None = None,
        token_context: dict[str, Any] | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        if not self.is_ready(self.settings):
            return self._fallback().answer_question(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
                debug=debug,
            )

        cleaned_message = message.strip()
        if not cleaned_message:
            return self._fallback().answer_question(
                message=message,
                chain_id=chain_id,
                token_context=token_context,
                debug=debug,
            )

        request_id = f"openai-{uuid.uuid4().hex}"
        started_at = time.perf_counter()
        normalized_intent = f"openai:{self._classify_intent(cleaned_message, token_context=token_context)}"

        try:
            answer_text, tool_calls = self._run_openai_tool_loop(
                message=cleaned_message,
                chain_id=chain_id,
                token_context=token_context,
            )

            if not tool_calls:
                raise RuntimeError("OpenAI agent returned no tool calls.")
            if not answer_text:
                raise RuntimeError("OpenAI agent returned an empty answer.")
            if self._contains_forbidden_language(answer_text):
                raise RuntimeError("OpenAI agent produced disallowed recommendation language.")

            evidence_used = self._build_evidence(tool_calls)
            missing_data = self._build_missing_data(tool_calls)
            response = self._response(
                answer=answer_text,
                evidence_used=evidence_used,
                missing_data=missing_data,
                tool_calls=tool_calls,
                debug=debug,
            )
            full_tool_trace = self._full_tool_trace(tool_calls)
            total_latency_ms = self._latency_ms(started_at)
            run_status = self._derive_run_status(tool_calls, missing_data)
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
        except Exception:
            return self._fallback().answer_question(
                message=cleaned_message,
                chain_id=chain_id,
                token_context=token_context,
                debug=debug,
            )

    def _run_openai_tool_loop(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> tuple[str, list[ToolCallRecord]]:
        client = self._client()
        instructions = self._build_instructions()
        input_items: list[Any] = [
            {
                "role": "user",
                "content": self._build_user_content(
                    message=message,
                    chain_id=chain_id,
                    token_context=token_context,
                ),
            }
        ]
        tools = self._build_openai_tools()
        tool_calls: list[ToolCallRecord] = []

        for _round in range(self.MAX_TOOL_ROUNDS):
            response = client.responses.create(
                model=self.settings.openai_model,
                instructions=instructions,
                tools=tools,
                input=input_items,
            )
            output_items = list(getattr(response, "output", []) or [])
            function_items = [
                item for item in output_items if self._item_attr(item, "type") == "function_call"
            ]

            if not function_items:
                answer_text = self._extract_output_text(response, output_items)
                return answer_text.strip(), tool_calls

            input_items.extend(output_items)

            for item in function_items:
                record = self._execute_function_call(item)
                tool_calls.append(record)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": self._item_attr(item, "call_id"),
                        "output": record.result.model_dump_json(),
                    }
                )

        raise RuntimeError("OpenAI agent exceeded the maximum tool-call rounds.")

    def _execute_function_call(self, item: Any) -> ToolCallRecord:
        tool_name = str(self._item_attr(item, "name") or "").strip()
        arguments_raw = self._item_attr(item, "arguments")
        started_at = time.perf_counter()

        try:
            parsed_args = json.loads(arguments_raw) if isinstance(arguments_raw, str) else arguments_raw
            if not isinstance(parsed_args, dict):
                raise ValueError("Tool arguments were not a JSON object.")
            result = asyncio.run(self.registry.call_tool(tool_name, parsed_args))
        except Exception as exc:
            parsed_args = parsed_args if isinstance(locals().get("parsed_args"), dict) else {}
            result = AgentToolResult(
                skill_name="openai_function_call",
                tool_name=tool_name or "unknown_tool",
                input_args=parsed_args,
                source="openai_agent",
                status="error",
                latency_ms=self._latency_ms(started_at),
                fetched_at=self._now(),
                data=None,
                error=str(exc),
            )

        alias = str(self._item_attr(item, "call_id") or tool_name or "openai_tool_call")
        return ToolCallRecord(
            alias=alias,
            tool_name=tool_name or "unknown_tool",
            input_args=result.input_args,
            result=result,
        )

    def _build_evidence(self, tool_calls: list[ToolCallRecord]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for record in tool_calls:
            entry: dict[str, Any] = {
                "type": record.tool_name,
                "source": record.result.source,
                "status": record.result.status,
            }
            data = self._tool_dict(record.result)
            items = self._tool_items(record.result)
            if items:
                entry["match_count"] = len(items)
                entry["top_results"] = [self._item_label(item) for item in items[:3]]
            elif "match_count" in data:
                entry["match_count"] = data.get("match_count")
            if "metadata" in data and isinstance(data["metadata"], dict):
                entry["token"] = data["metadata"].get("symbol") or data["metadata"].get("name")
            if "dynamic_market_data" in data and isinstance(data["dynamic_market_data"], dict):
                dynamic = data["dynamic_market_data"]
                entry["percent_change_24h"] = dynamic.get("percentChange24h")
                entry["liquidity"] = dynamic.get("liquidity")
                entry["volume_24h"] = dynamic.get("volume24h")
            if "riskLevelEnum" in data:
                entry["risk_level_enum"] = data.get("riskLevelEnum")
            if "insight" in data and isinstance(data["insight"], dict):
                insight = data["insight"]
                entry["attention_score"] = insight.get("attention_score")
                entry["label"] = insight.get("label")
            if "record_counts" in data and isinstance(data["record_counts"], dict):
                entry["record_counts"] = data["record_counts"]
            if record.result.error:
                entry["error"] = record.result.error
            evidence.append(entry)
        return evidence

    def _build_missing_data(self, tool_calls: list[ToolCallRecord]) -> list[str]:
        missing: list[str] = []
        for record in tool_calls:
            if record.result.status in {"error", "empty"}:
                missing.append(record.tool_name)
                continue

            if record.result.data is None:
                missing.append(record.tool_name)
                continue

            if isinstance(record.result.data, dict):
                if not record.result.data:
                    missing.append(record.tool_name)
                elif "items" in record.result.data and not self._tool_items(record.result):
                    missing.append(record.tool_name)
        return list(dict.fromkeys(missing))

    def _build_openai_tools(self) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = []
        for descriptor in self.registry.list_agent_tools():
            registered = self.registry.get_tool(descriptor["name"])
            definitions.append(
                {
                    "type": "function",
                    "name": registered.name,
                    "description": registered.description,
                    "parameters": self._parameter_schema(registered),
                    "strict": True,
                }
            )
        return definitions

    def _parameter_schema(self, tool: RegisteredTool) -> dict[str, Any]:
        properties = {
            name: self._descriptor_to_json_schema(descriptor)
            for name, descriptor in tool.input_schema.items()
        }
        signature = inspect.signature(tool.callable)
        required = [
            name
            for name, parameter in signature.parameters.items()
            if name in properties and parameter.default is inspect._empty
        ]
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    def _descriptor_to_json_schema(self, descriptor: Any) -> dict[str, Any]:
        if not isinstance(descriptor, str):
            return {"type": "string"}

        normalized = descriptor.strip()
        if not normalized:
            return {"type": "string"}

        parts = [part.strip() for part in normalized.split("|") if part.strip()]
        base_types = {"string", "integer", "boolean", "number", "null"}

        if len(parts) == 2 and "null" in parts and any(part in base_types for part in parts):
            non_null = next((part for part in parts if part != "null"), "string")
            return {
                "anyOf": [
                    {"type": non_null if non_null in base_types else "string"},
                    {"type": "null"},
                ]
            }

        if len(parts) == 1 and parts[0] in base_types:
            return {"type": parts[0]}

        if all(part not in base_types for part in parts):
            return {"type": "string", "enum": parts}

        return {"type": "string"}

    def _build_instructions(self) -> str:
        return (
            "You are the optional OpenAI mode for the trust-trace market-intelligence backend. "
            "Use only the provided function tools to answer the user. "
            "You must call at least one tool before giving a final answer. "
            "Do not invent market, audit, smart-money, or KOL data. "
            "If a tool returns missing or empty data, say that clearly instead of guessing. "
            "Do not give buy or sell recommendations, do not promise profit, and do not describe any token as risk-free or guaranteed safe. "
            "Keep the answer concise and framed as market research."
        )

    def _build_user_content(
        self,
        *,
        message: str,
        chain_id: str | None,
        token_context: dict[str, Any] | None,
    ) -> str:
        payload = {
            "message": message,
            "chain_id": chain_id,
            "token_context": token_context,
            "kol_data_mode": self.settings.kol_data_mode,
            "enabled_chains": self.settings.enabled_chains,
        }
        return json.dumps(payload, default=str, separators=(",", ":"), ensure_ascii=True)

    def _extract_output_text(self, response: Any, output_items: list[Any]) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        fragments: list[str] = []
        for item in output_items:
            if self._item_attr(item, "type") != "message":
                continue
            content = self._item_attr(item, "content") or []
            if not isinstance(content, list):
                continue
            for block in content:
                block_type = self._item_attr(block, "type")
                if block_type in {"output_text", "text"}:
                    text = self._item_attr(block, "text")
                    if isinstance(text, str) and text.strip():
                        fragments.append(text.strip())
        return " ".join(fragments).strip()

    def _contains_forbidden_language(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in FORBIDDEN_LANGUAGE_PATTERNS)

    def _item_attr(self, item: Any, name: str) -> Any:
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name, None)

    def _client(self) -> Any:
        if self.client is not None:
            return self.client
        if OpenAI is None:
            raise RuntimeError("OpenAI package is not installed.")
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        return self.client

    def _fallback(self) -> ChatAgentService:
        return ChatAgentService(self.db, registry=self.registry)


def get_agent_service(
    db: Session,
    *,
    registry: ToolRegistry | None = None,
) -> ChatAgentService:
    settings = get_settings()
    if settings.agent_mode == "openai":
        return OpenAIAgentService(db, registry=registry, settings=settings)
    return ChatAgentService(db, registry=registry)


__all__ = ["OpenAIAgentService", "get_agent_service"]
