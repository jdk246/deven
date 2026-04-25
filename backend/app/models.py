from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Token(Base):
    __tablename__ = "tokens"

    chain_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contract_address: Mapped[str] = mapped_column(String(255), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    decimals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TokenSnapshot(Base):
    __tablename__ = "token_snapshots"
    __table_args__ = (
        Index("ix_token_snapshots_token_ts", "chain_id", "contract_address", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_change_1h: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_change_4h: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_change_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    fdv: Mapped[float | None] = mapped_column(Float, nullable=True)
    holders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top10_holders_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    kol_holders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kol_holding_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    smart_money_holding_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class TokenAudit(Base):
    __tablename__ = "token_audits"
    __table_args__ = (
        Index("ix_token_audits_token_ts", "chain_id", "contract_address", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    has_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_level_enum: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buy_tax: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_tax: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_items_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SmartMoneySignal(Base):
    __tablename__ = "smart_money_signals"
    __table_args__ = (
        Index(
            "ix_smart_money_signals_token_ts",
            "chain_id",
            "contract_address",
            "ts",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(32), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    smart_money_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signal_trigger_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    total_token_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class KOLProfile(Base):
    __tablename__ = "kol_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    handle: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class KOLWallet(Base):
    __tablename__ = "kol_wallets"
    __table_args__ = (
        UniqueConstraint("kol_id", "chain_id", "address", name="uq_kol_wallet_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kol_id: Mapped[int] = mapped_column(
        ForeignKey("kol_profiles.id"),
        nullable=False,
        index=True,
    )
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class KOLPost(Base):
    __tablename__ = "kol_posts"
    __table_args__ = (
        Index("ix_kol_posts_kol_created_at", "kol_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kol_id: Mapped[int] = mapped_column(
        ForeignKey("kol_profiles.id"),
        nullable=False,
        index=True,
    )
    external_post_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repost_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TokenMention(Base):
    __tablename__ = "token_mentions"
    __table_args__ = (
        Index("ix_token_mentions_token", "chain_id", "contract_address"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("kol_posts.id"),
        nullable=False,
        index=True,
    )
    chain_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol_text: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mention_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class KOLWalletPosition(Base):
    __tablename__ = "kol_wallet_positions"
    __table_args__ = (
        Index(
            "ix_kol_wallet_positions_wallet_ts",
            "kol_wallet_id",
            "ts",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kol_wallet_id: Mapped[int] = mapped_column(
        ForeignKey("kol_wallets.id"),
        nullable=False,
        index=True,
    )
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_change_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TokenInsight(Base):
    __tablename__ = "token_insights"
    __table_args__ = (
        Index("ix_token_insights_token_ts", "chain_id", "contract_address", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    market_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    kol_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    smart_money_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_intent: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)


class KOLCall(Base):
    __tablename__ = "kol_calls"
    __table_args__ = (
        UniqueConstraint("post_id", "chain_id", "contract_address", name="uq_kol_calls_post_token"),
        Index("ix_kol_calls_kol_created_at", "kol_id", "post_created_at"),
        Index("ix_kol_calls_token", "chain_id", "contract_address"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kol_id: Mapped[int] = mapped_column(
        ForeignKey("kol_profiles.id"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("kol_posts.id"),
        nullable=False,
        index=True,
    )
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    symbol_text: Mapped[str | None] = mapped_column(String(32), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    raw_mention_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class KOLCallPriceObservation(Base):
    __tablename__ = "kol_call_price_observations"
    __table_args__ = (
        UniqueConstraint("kol_call_id", name="uq_kol_call_price_observation_call"),
        Index("ix_kol_call_price_observations_status", "evaluation_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kol_call_id: Mapped[int] = mapped_column(
        ForeignKey("kol_calls.id"),
        nullable=False,
        index=True,
    )
    price_at_post: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_1h: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_6h: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_1h: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_6h: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_window: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    price_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class KOLTrackRecordScore(Base):
    __tablename__ = "kol_track_record_scores"
    __table_args__ = (
        UniqueConstraint("kol_id", "window", name="uq_kol_track_record_scores_kol_window"),
        Index("ix_kol_track_record_scores_window_score", "window", "track_record_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kol_id: Mapped[int] = mapped_column(
        ForeignKey("kol_profiles.id"),
        nullable=False,
        index=True,
    )
    window: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    total_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluated_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bullish_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bearish_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    neutral_or_unknown_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    misses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hit_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_return_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_return_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_primary_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    track_record_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    rationale_json: Mapped[str | None] = mapped_column(Text, nullable=True)
