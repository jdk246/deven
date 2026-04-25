from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KOLPost, TokenMention
from app.services.token_mapping import SOLANA_CHAIN_ID, TokenMappingService


@dataclass(frozen=True)
class ExtractedMention:
    mention_type: str
    chain_id: str | None
    contract_address: str | None
    symbol_text: str | None
    confidence: float
    is_resolved: bool


class TokenExtractionService:
    EVM_ADDRESS_PATTERN = (
        r"(?<![A-Za-z0-9])"
        r"(0x[a-fA-F0-9]{40})"
        r"(?![A-Za-z0-9])"
    )
    SOLANA_ADDRESS_PATTERN = (
        r"(?<![A-Za-z0-9])"
        r"([1-9A-HJ-NP-Za-km-z]{32,44})"
        r"(?![A-Za-z0-9])"
    )
    CASHTAG_PATTERN = (
        r"(?<![A-Za-z0-9_])"
        r"\$([A-Za-z][A-Za-z0-9]{1,14})"
        r"(?![A-Za-z0-9_])"
    )
    SYMBOL_TEXT_PATTERNS = (
        r"(?i:\b(?:ticker|symbol|token|pair)\s+)([A-Z][A-Z0-9]{1,9})\b",
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.mapping_service = TokenMappingService(db)

    def sync_posts(self, posts: list[KOLPost]) -> dict[str, int]:
        summary = {
            "mentions_upserted": 0,
            "mentions_resolved": 0,
            "mentions_unresolved": 0,
        }

        for post in posts:
            mapped_mentions = self.sync_post(post)
            for mention in mapped_mentions:
                summary["mentions_upserted"] += 1
                if mention.is_resolved:
                    summary["mentions_resolved"] += 1
                else:
                    summary["mentions_unresolved"] += 1

        return summary

    def sync_post(self, post: KOLPost) -> list[TokenMention]:
        if post.id is None:
            self.db.flush()

        desired_mentions = self.extract_mentions(post.text)
        existing_mentions = self.db.execute(
            select(TokenMention).where(TokenMention.post_id == post.id)
        ).scalars().all()

        existing_map: dict[tuple[Any, ...], list[TokenMention]] = {}
        for mention in existing_mentions:
            existing_map.setdefault(self._source_key(mention), []).append(mention)

        stored_mentions: list[TokenMention] = []

        for extracted in desired_mentions:
            key = self._source_key(extracted)
            candidates = existing_map.get(key, [])
            mention = candidates.pop(0) if candidates else None

            if mention is None:
                mention = TokenMention(post_id=post.id, mention_type=extracted.mention_type)

            mention.post_id = post.id
            mention.chain_id = extracted.chain_id
            mention.contract_address = extracted.contract_address
            mention.symbol_text = extracted.symbol_text
            mention.mention_type = extracted.mention_type
            mention.confidence = extracted.confidence
            mention.is_resolved = extracted.is_resolved
            self.db.add(mention)
            stored_mentions.append(mention)

        for leftover_mentions in existing_map.values():
            for mention in leftover_mentions:
                self.db.delete(mention)

        self.db.flush()

        self.mapping_service.map_mentions(stored_mentions)
        return stored_mentions

    def extract_mentions(self, text: str | None) -> list[ExtractedMention]:
        if not text:
            return []

        mentions: list[ExtractedMention] = []
        seen_keys: set[tuple[Any, ...]] = set()

        import re

        for match in re.finditer(self.EVM_ADDRESS_PATTERN, text):
            mention = ExtractedMention(
                mention_type="contract_address",
                chain_id=None,
                contract_address=match.group(1).strip(),
                symbol_text=None,
                confidence=0.35,
                is_resolved=False,
            )
            key = self._source_key(mention)
            if key not in seen_keys:
                mentions.append(mention)
                seen_keys.add(key)

        for match in re.finditer(self.SOLANA_ADDRESS_PATTERN, text):
            address = match.group(1)
            if address.lower().startswith("0x"):
                continue
            mention = ExtractedMention(
                mention_type="contract_address",
                chain_id=SOLANA_CHAIN_ID,
                contract_address=address.strip(),
                symbol_text=None,
                confidence=0.4,
                is_resolved=False,
            )
            key = self._source_key(mention)
            if key not in seen_keys:
                mentions.append(mention)
                seen_keys.add(key)

        for match in re.finditer(self.CASHTAG_PATTERN, text):
            symbol = match.group(1).upper()
            mention = ExtractedMention(
                mention_type="cashtag",
                chain_id=None,
                contract_address=None,
                symbol_text=symbol,
                confidence=0.3,
                is_resolved=False,
            )
            key = self._source_key(mention)
            if key not in seen_keys:
                mentions.append(mention)
                seen_keys.add(key)

        for pattern in self.SYMBOL_TEXT_PATTERNS:
            for match in re.finditer(pattern, text):
                symbol = match.group(1).upper()
                mention = ExtractedMention(
                    mention_type="symbol_text",
                    chain_id=None,
                    contract_address=None,
                    symbol_text=symbol,
                    confidence=0.25,
                    is_resolved=False,
                )
                key = self._source_key(mention)
                if key not in seen_keys:
                    mentions.append(mention)
                    seen_keys.add(key)

        return mentions

    def _source_key(self, mention: ExtractedMention | TokenMention) -> tuple[Any, ...]:
        mention_type = mention.mention_type
        contract_address = (mention.contract_address or "").lower()
        symbol_text = self._normalize_symbol(mention.symbol_text) or ""

        if mention_type == "contract_address":
            return (mention_type, contract_address, "")
        if mention_type in {"cashtag", "symbol_text"}:
            return (mention_type, "", symbol_text)
        return (mention_type, contract_address, symbol_text)

    def _normalize_symbol(self, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().upper()
        return stripped or None
