from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ChainOption(BaseModel):
    chain_id: str
    name: str
    short_name: str
    platform: str
    enabled_by_default: bool
    enabled: bool


class AdminRefreshRequest(BaseModel):
    jobs: list[Literal["market", "audits", "smart_money", "kols", "insights", "kol_performance"]] = Field(
        default_factory=lambda: ["market", "audits", "smart_money", "kols", "insights", "kol_performance"]
    )
    chains: list[str] | None = None
    limit_per_chain: int = Field(default=20, ge=1, le=100)


class AdminRefreshChainSummary(BaseModel):
    chain_id: str
    chain_name: str
    tokens_seen: int = 0
    tokens_upserted: int = 0
    snapshots_created: int = 0
    audits_created: int = 0
    signals_upserted: int = 0
    errors: list[str] = Field(default_factory=list)


class AdminRefreshKOLSummary(BaseModel):
    mode: Literal["seed", "live"]
    profiles_seen: int = 0
    profiles_upserted: int = 0
    wallets_upserted: int = 0
    posts_seen: int = 0
    posts_upserted: int = 0
    mentions_upserted: int = 0
    mentions_resolved: int = 0
    mentions_unresolved: int = 0
    errors: list[str] = Field(default_factory=list)


class AdminRefreshInsightSummary(BaseModel):
    tokens_seen: int = 0
    insights_created: int = 0
    errors: list[str] = Field(default_factory=list)


class AdminRefreshKOLPerformanceSummary(BaseModel):
    calls_created: int = 0
    calls_evaluated: int = 0
    scores_updated: int = 0
    warnings: list[str] = Field(default_factory=list)


class AdminRefreshResponse(BaseModel):
    status: Literal["ok"] = "ok"
    jobs: list[str]
    chains: list[ChainOption]
    limit_per_chain: int
    summary: list[AdminRefreshChainSummary]
    kol_summary: AdminRefreshKOLSummary | None = None
    insight_summary: AdminRefreshInsightSummary | None = None
    kol_performance_summary: AdminRefreshKOLPerformanceSummary | None = None
    errors: list[str] = Field(default_factory=list)


class TokenBase(BaseModel):
    chain_id: str
    contract_address: str
    symbol: str | None = None
    name: str | None = None
    icon_url: str | None = None
    decimals: int | None = None
    links_json: str | None = None


class TokenRead(TokenBase):
    first_seen_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenListItem(BaseModel):
    chain_id: str
    chain_name: str
    chain_short_name: str
    contract_address: str
    symbol: str | None = None
    name: str | None = None
    icon_url: str | None = None
    latest_price: float | None = None
    latest_percent_change_24h: float | None = None
    latest_volume_24h: float | None = None
    latest_market_cap: float | None = None
    holders: int | None = None
    risk_level_enum: str | None = None
    risk_level: int | None = None
    latest_snapshot_at: datetime | None = None
    latest_audit_at: datetime | None = None
    updated_at: datetime


class TokenListResponse(BaseModel):
    items: list[TokenListItem]
    available_chains: list[ChainOption]


class AgentToolResult(BaseModel):
    skill_name: str
    tool_name: str
    input_args: dict[str, Any] = Field(default_factory=dict)
    source: str
    status: str
    latency_ms: int = 0
    fetched_at: datetime
    data: Any = None
    error: str | None = None

    model_config = ConfigDict(extra="forbid")


class AgentTokenContext(BaseModel):
    chain_id: str | None = None
    contract_address: str | None = None
    symbol: str | None = None
    name: str | None = None


class AgentQueryRequest(BaseModel):
    message: str = Field(min_length=1)
    chain_id: str | None = None
    token_context: AgentTokenContext | None = None
    debug: bool = False


class AgentQueryResponse(BaseModel):
    answer: str
    evidence_used: list[dict[str, Any]] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    disclaimer: str


class AgentHealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    agent_mode: Literal["deterministic", "openai"] = "deterministic"
    data_mode: Literal["seed", "live"]
    openai_ready: bool = False


class AgentToolDescriptor(BaseModel):
    name: str
    category: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class AgentToolListResponse(BaseModel):
    items: list[AgentToolDescriptor]


class AgentExampleItem(BaseModel):
    title: str
    description: str
    endpoint: str
    method: Literal["GET", "POST"]
    request_body: dict[str, Any] | None = None
    expected_response_shape: dict[str, Any] = Field(default_factory=dict)


class AgentExamplesResponse(BaseModel):
    items: list[AgentExampleItem]


class BackendValidationCheck(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    expected: int | str
    actual: int | str | None = None
    fix_hint: str


class BackendValidationResponse(BaseModel):
    status: Literal["pass", "warn", "fail"]
    checks: list[BackendValidationCheck]
