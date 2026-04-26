from functools import lru_cache
from json import loads
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = BACKEND_DIR / "trust_trace.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="trust-trace", alias="APP_NAME")
    backend_host: str = Field(default="127.0.0.1", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    binance_skills_base_url: str = Field(
        default="https://web3.binance.com",
        alias="BINANCE_SKILLS_BASE_URL",
    )
    binance_icon_base_url: str = Field(
        default="https://bin.bnbstatic.com",
        alias="BINANCE_ICON_BASE_URL",
    )
    binance_request_timeout_seconds: float = Field(
        default=20.0,
        alias="BINANCE_REQUEST_TIMEOUT_SECONDS",
    )
    binance_max_retries: int = Field(default=2, alias="BINANCE_MAX_RETRIES")
    agent_mode: str = Field(default="deterministic", alias="AGENT_MODE")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-nano", alias="OPENAI_MODEL")
    openai_request_timeout_seconds: float = Field(
        default=20.0,
        alias="OPENAI_REQUEST_TIMEOUT_SECONDS",
    )
    openai_max_total_seconds: float = Field(
        default=30.0,
        alias="OPENAI_MAX_TOTAL_SECONDS",
    )
    openai_max_tool_rounds: int = Field(default=3, alias="OPENAI_MAX_TOOL_ROUNDS")
    openai_max_retries: int = Field(default=0, alias="OPENAI_MAX_RETRIES")
    kol_data_mode: str = Field(default="seed", alias="KOL_DATA_MODE")
    x_bearer_token: str | None = Field(default=None, alias="X_BEARER_TOKEN")
    enabled_chains: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["56", "CT_501"],
        alias="ENABLED_CHAINS",
    )
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}",
        alias="DATABASE_URL",
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="BACKEND_CORS_ORIGINS",
    )
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_api_base_url: str = Field(
        default="http://127.0.0.1:8000",
        alias="TELEGRAM_API_BASE_URL",
    )
    telegram_poll_timeout_seconds: int = Field(
        default=30,
        alias="TELEGRAM_POLL_TIMEOUT_SECONDS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        def normalize_loopback_origins(origins: list[str]) -> list[str]:
            normalized: list[str] = []

            def add(origin: str) -> None:
                if origin and origin not in normalized:
                    normalized.append(origin)

            for origin in origins:
                add(origin)

                if origin == "http://localhost:5173":
                    add("http://127.0.0.1:5173")
                elif origin == "http://127.0.0.1:5173":
                    add("http://localhost:5173")

            return normalized

        if value is None or value == "":
            return normalize_loopback_origins(["http://localhost:5173"])

        if isinstance(value, str):
            raw_value = value.strip()

            if raw_value.startswith("["):
                parsed_value = loads(raw_value)
                parsed_origins = [item.strip() for item in parsed_value if item.strip()]
                return normalize_loopback_origins(parsed_origins)

            parsed_origins = [item.strip() for item in raw_value.split(",") if item.strip()]
            return normalize_loopback_origins(parsed_origins)

        if isinstance(value, list):
            parsed_origins = [str(item).strip() for item in value if str(item).strip()]
            return normalize_loopback_origins(parsed_origins)

        raise ValueError("Invalid BACKEND_CORS_ORIGINS value")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        if value is None or value == "":
            return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

        if isinstance(value, str):
            raw_value = value.strip()

            if raw_value.startswith("sqlite:///./"):
                relative_path = raw_value.removeprefix("sqlite:///./")
                return f"sqlite:///{(REPO_ROOT / relative_path).as_posix()}"

            return raw_value

        raise ValueError("Invalid DATABASE_URL value")

    @field_validator("enabled_chains", mode="before")
    @classmethod
    def parse_enabled_chains(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return ["56", "CT_501"]

        if isinstance(value, str):
            raw_value = value.strip()

            if raw_value.startswith("["):
                parsed_value = loads(raw_value)
                return [str(item).strip() for item in parsed_value if str(item).strip()]

            return [item.strip() for item in raw_value.split(",") if item.strip()]

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        raise ValueError("Invalid ENABLED_CHAINS value")

    @field_validator("kol_data_mode", mode="before")
    @classmethod
    def normalize_kol_data_mode(cls, value: Any) -> str:
        if value is None or value == "":
            return "seed"

        normalized = str(value).strip().lower()
        if normalized not in {"seed", "live"}:
            raise ValueError("KOL_DATA_MODE must be either 'seed' or 'live'")
        return normalized

    @field_validator("agent_mode", mode="before")
    @classmethod
    def normalize_agent_mode(cls, value: Any) -> str:
        if value is None or value == "":
            return "deterministic"

        normalized = str(value).strip().lower()
        if normalized not in {"deterministic", "openai"}:
            raise ValueError("AGENT_MODE must be either 'deterministic' or 'openai'")
        return normalized

    @field_validator("x_bearer_token", "openai_api_key", "telegram_bot_token", mode="before")
    @classmethod
    def normalize_optional_token(cls, value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
