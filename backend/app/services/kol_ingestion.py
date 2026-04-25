from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR, Settings, get_settings
from app.models import KOLPost, KOLProfile, KOLWallet
from app.services.sentiment import RuleBasedSentimentClassifier
from app.services.token_extraction import TokenExtractionService

DATA_DIR = BACKEND_DIR / "data"
SEED_PROFILES_PATH = DATA_DIR / "kols.yaml"
SEED_POSTS_PATH = DATA_DIR / "kol_posts_seed.json"


class KOLIngestionService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.data_dir = data_dir or DATA_DIR
        self.sentiment_classifier = RuleBasedSentimentClassifier()

    def run_refresh(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "mode": self.settings.kol_data_mode,
            "profiles_seen": 0,
            "profiles_upserted": 0,
            "wallets_upserted": 0,
            "posts_seen": 0,
            "posts_upserted": 0,
            "mentions_upserted": 0,
            "mentions_resolved": 0,
            "mentions_unresolved": 0,
            "errors": [],
        }

        if self.settings.kol_data_mode == "seed":
            self._run_seed_refresh(summary)
            return summary

        summary["errors"].append(
            "Live KOL ingestion is not implemented yet. Use KOL_DATA_MODE=seed for now."
        )
        return summary

    def _run_seed_refresh(self, summary: dict[str, Any]) -> None:
        try:
            profile_rows = self._load_yaml_rows(self.data_dir / SEED_PROFILES_PATH.name)
        except Exception as exc:
            summary["errors"].append(f"Failed to load seed KOL profiles: {exc}")
            return

        profile_map = self._upsert_profiles(profile_rows, summary)
        if not self._commit_or_recover(summary, "Failed to write KOL profiles"):
            return

        try:
            post_rows = self._load_json_rows(self.data_dir / SEED_POSTS_PATH.name)
        except Exception as exc:
            summary["errors"].append(f"Failed to load seed KOL posts: {exc}")
            return

        processed_posts = self._upsert_posts(post_rows, profile_map, summary)
        self.db.flush()
        extraction_summary = TokenExtractionService(self.db).sync_posts(processed_posts)
        summary["mentions_upserted"] += extraction_summary["mentions_upserted"]
        summary["mentions_resolved"] += extraction_summary["mentions_resolved"]
        summary["mentions_unresolved"] += extraction_summary["mentions_unresolved"]
        self._commit_or_recover(summary, "Failed to write KOL posts")

    def _upsert_profiles(
        self,
        rows: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> dict[str, KOLProfile]:
        profile_map: dict[str, KOLProfile] = {}

        for row in rows:
            summary["profiles_seen"] += 1
            handle = self._normalize_handle(row.get("handle"))
            if handle is None:
                summary["errors"].append("Skipping KOL profile with missing handle.")
                continue

            profile = self._find_profile(handle)
            if profile is None:
                profile = KOLProfile(handle=handle)

            profile.display_name = self._coalesce_string(
                row.get("display_name") or row.get("displayName"),
                profile.display_name,
            )
            profile.category = self._coalesce_string(row.get("category"), profile.category)
            profile.priority = self._coalesce_int(row.get("priority"), profile.priority)
            profile.notes = self._coalesce_string(row.get("notes"), profile.notes)
            profile.updated_at = self._now()
            self.db.add(profile)
            self.db.flush()

            summary["profiles_upserted"] += 1
            profile_map[handle] = profile
            summary["wallets_upserted"] += self._upsert_wallets(
                profile=profile,
                wallets=row.get("wallets"),
                summary=summary,
            )

        return profile_map

    def _upsert_posts(
        self,
        rows: list[dict[str, Any]],
        profile_map: dict[str, KOLProfile],
        summary: dict[str, Any],
    ) -> list[KOLPost]:
        processed_posts: list[KOLPost] = []

        for row in rows:
            summary["posts_seen"] += 1
            handle = self._normalize_handle(row.get("handle"))
            if handle is None:
                summary["errors"].append("Skipping KOL post with missing handle.")
                continue

            profile = profile_map.get(handle)
            if profile is None:
                profile = self._get_or_create_placeholder_profile(handle, summary)
                if profile is None:
                    continue
                profile_map[handle] = profile

            text = self._string_value(row.get("text"))
            if text is None:
                summary["errors"].append(f"Skipping KOL post with missing text for @{handle}.")
                continue

            created_at = self._datetime_value(row.get("created_at"))
            post = self._find_existing_post(
                kol_id=profile.id,
                external_post_id=self._string_value(row.get("external_post_id")),
                url=self._string_value(row.get("url")),
                created_at=created_at,
                text=text,
            )

            if post is None:
                post = KOLPost(kol_id=profile.id, text=text, source_mode="seed")

            post.kol_id = profile.id
            post.external_post_id = self._string_value(row.get("external_post_id"))
            post.created_at = created_at
            post.text = text
            post.url = self._string_value(row.get("url"))
            post.like_count = self._int_value(row.get("like_count"))
            post.repost_count = self._int_value(row.get("repost_count"))
            post.reply_count = self._int_value(row.get("reply_count"))
            post.view_count = self._int_value(row.get("view_count"))
            post.source_mode = self._normalize_source_mode(row.get("source_mode"))
            sentiment = self.sentiment_classifier.classify(text)
            post.sentiment = sentiment.label
            post.sentiment_score = sentiment.score
            post.raw_json = self._json_text(row)
            self.db.add(post)
            summary["posts_upserted"] += 1
            processed_posts.append(post)

        return processed_posts

    def _upsert_wallets(
        self,
        *,
        profile: KOLProfile,
        wallets: Any,
        summary: dict[str, Any],
    ) -> int:
        if not isinstance(wallets, list):
            return 0

        upserted = 0

        for wallet_row in wallets:
            wallet_data = wallet_row if isinstance(wallet_row, dict) else {}
            chain_id = self._string_value(wallet_data.get("chain_id") or wallet_data.get("chain"))
            address = self._string_value(wallet_data.get("address"))

            if chain_id is None or address is None:
                if wallet_row:
                    summary["errors"].append(
                        f"Skipping malformed wallet entry for @{profile.handle}."
                    )
                continue

            wallet = self.db.execute(
                select(KOLWallet).where(
                    KOLWallet.kol_id == profile.id,
                    KOLWallet.chain_id == chain_id,
                    KOLWallet.address == address,
                )
            ).scalar_one_or_none()

            if wallet is None:
                wallet = KOLWallet(
                    kol_id=profile.id,
                    chain_id=chain_id,
                    address=address,
                )

            wallet.source_type = self._coalesce_string(
                wallet_data.get("source_type") or wallet_data.get("sourceType"),
                wallet.source_type,
            )
            wallet.source_url = self._coalesce_string(
                wallet_data.get("source_url") or wallet_data.get("sourceUrl"),
                wallet.source_url,
            )
            confidence = self._float_value(wallet_data.get("confidence"))
            if confidence is not None:
                wallet.confidence = confidence
            elif wallet.confidence is None:
                wallet.confidence = 0.5
            self.db.add(wallet)
            upserted += 1

        return upserted

    def _get_or_create_placeholder_profile(
        self,
        handle: str,
        summary: dict[str, Any],
    ) -> KOLProfile | None:
        profile = self._find_profile(handle)
        if profile is not None:
            return profile

        profile = KOLProfile(
            handle=handle,
            display_name=handle.replace("_", " ").title(),
            category="unclassified",
            notes="Created from KOL seed post ingestion.",
            updated_at=self._now(),
        )
        self.db.add(profile)

        try:
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            summary["errors"].append(f"Failed to create placeholder KOL profile @{handle}: {exc}")
            return None

        summary["profiles_upserted"] += 1
        return profile

    def _find_profile(self, handle: str) -> KOLProfile | None:
        return self.db.execute(
            select(KOLProfile).where(KOLProfile.handle == handle)
        ).scalar_one_or_none()

    def _find_existing_post(
        self,
        *,
        kol_id: int,
        external_post_id: str | None,
        url: str | None,
        created_at: datetime | None,
        text: str,
    ) -> KOLPost | None:
        if external_post_id:
            post = self.db.execute(
                select(KOLPost).where(
                    KOLPost.kol_id == kol_id,
                    KOLPost.external_post_id == external_post_id,
                )
            ).scalar_one_or_none()
            if post is not None:
                return post

        if url:
            post = self.db.execute(
                select(KOLPost).where(
                    KOLPost.kol_id == kol_id,
                    KOLPost.url == url,
                )
            ).scalar_one_or_none()
            if post is not None:
                return post

        return self.db.execute(
            select(KOLPost).where(
                KOLPost.kol_id == kol_id,
                KOLPost.created_at == created_at,
                KOLPost.text == text,
            )
        ).scalar_one_or_none()

    def _load_yaml_rows(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or []

        if not isinstance(payload, list):
            raise ValueError(f"Expected a list in {path.name}.")

        return [row for row in payload if isinstance(row, dict)]

    def _load_json_rows(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, list):
            raise ValueError(f"Expected a list in {path.name}.")

        return [row for row in payload if isinstance(row, dict)]

    def _commit_or_recover(
        self,
        summary: dict[str, Any],
        message: str,
    ) -> bool:
        try:
            self.db.commit()
            return True
        except Exception as exc:
            self.db.rollback()
            summary["errors"].append(f"{message}: {exc}")
            return False

    def _normalize_handle(self, value: Any) -> str | None:
        handle = self._string_value(value)
        if handle is None:
            return None
        normalized = handle.lstrip("@").strip().lower()
        return normalized or None

    def _normalize_source_mode(self, value: Any) -> str:
        normalized = self._string_value(value)
        if normalized is None:
            return self.settings.kol_data_mode

        lowered = normalized.lower()
        return lowered if lowered in {"seed", "live"} else self.settings.kol_data_mode

    def _datetime_value(self, value: Any) -> datetime | None:
        raw_value = self._string_value(value)
        if raw_value is None:
            return None

        try:
            if raw_value.endswith("Z"):
                return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    def _json_text(self, value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str, separators=(",", ":"))

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _string_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    def _int_value(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return None
        return None

    def _float_value(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _coalesce_string(self, new_value: Any, existing: str | None) -> str | None:
        parsed = self._string_value(new_value)
        return parsed if parsed is not None else existing

    def _coalesce_int(self, new_value: Any, existing: int | None) -> int | None:
        parsed = self._int_value(new_value)
        return parsed if parsed is not None else existing
