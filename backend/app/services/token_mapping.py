from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import Token, TokenMention, TokenSnapshot

SOLANA_CHAIN_ID = "CT_501"


@dataclass(frozen=True)
class TokenCandidate:
    token: Token
    liquidity: float | None
    volume_24h: float | None


class TokenMappingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def map_mentions(self, mentions: list[TokenMention]) -> dict[str, int]:
        summary = {
            "mentions_resolved": 0,
            "mentions_unresolved": 0,
        }

        for mention in mentions:
            mapped = self.map_mention(mention)
            if mapped.is_resolved:
                summary["mentions_resolved"] += 1
            else:
                summary["mentions_unresolved"] += 1

        return summary

    def map_mention(self, mention: TokenMention) -> TokenMention:
        raw_chain_hint = mention.chain_id
        raw_contract_address = mention.contract_address
        raw_symbol = self._normalize_symbol(mention.symbol_text)

        mention.is_resolved = False
        mention.confidence = self._unresolved_confidence(mention.mention_type, raw_chain_hint)

        if mention.mention_type == "contract_address" and raw_contract_address:
            candidate = self._match_exact_contract_address(
                contract_address=raw_contract_address,
                chain_hint=raw_chain_hint,
            )
            if candidate is not None:
                mention.chain_id = candidate.chain_id
                mention.contract_address = candidate.contract_address
                mention.symbol_text = raw_symbol or self._normalize_symbol(candidate.symbol)
                mention.is_resolved = True
                mention.confidence = 1.0
                self.db.add(mention)
                return mention

            mention.chain_id = raw_chain_hint
            mention.contract_address = raw_contract_address
            mention.symbol_text = raw_symbol
            self.db.add(mention)
            return mention

        if mention.mention_type in {"cashtag", "symbol_text"} and raw_symbol:
            candidate, mapped_confidence = self._match_symbol(
                symbol=raw_symbol,
                mention_type=mention.mention_type,
            )
            if candidate is not None:
                mention.chain_id = candidate.chain_id
                mention.contract_address = candidate.contract_address
                mention.symbol_text = raw_symbol
                mention.is_resolved = True
                mention.confidence = mapped_confidence
                self.db.add(mention)
                return mention

            mention.chain_id = None
            mention.contract_address = None
            mention.symbol_text = raw_symbol
            self.db.add(mention)
            return mention

        self.db.add(mention)
        return mention

    def _match_exact_contract_address(
        self,
        *,
        contract_address: str,
        chain_hint: str | None,
    ) -> Token | None:
        normalized_address = contract_address.strip().lower()
        matches = self.db.execute(
            select(Token).where(func.lower(Token.contract_address) == normalized_address)
        ).scalars().all()

        if chain_hint:
            hinted_matches = [token for token in matches if token.chain_id == chain_hint]
            if len(hinted_matches) == 1:
                return hinted_matches[0]
            if len(hinted_matches) > 1:
                return None

        return matches[0] if len(matches) == 1 else None

    def _match_symbol(
        self,
        *,
        symbol: str,
        mention_type: str,
    ) -> tuple[Token | None, float]:
        tokens = self.db.execute(
            select(Token)
            .where(func.upper(Token.symbol) == symbol)
            .order_by(Token.updated_at.desc())
        ).scalars().all()

        if len(tokens) == 1:
            return tokens[0], 0.95 if mention_type == "cashtag" else 0.85
        if not tokens:
            return None, self._unresolved_confidence(mention_type, None)

        ranked_candidates = [self._build_candidate(token) for token in tokens]
        token = self._select_best_candidate(ranked_candidates)
        if token is None:
            return None, self._unresolved_confidence(mention_type, None)

        confidence = 0.9 if mention_type == "cashtag" else 0.8
        return token, confidence

    def _build_candidate(self, token: Token) -> TokenCandidate:
        latest_snapshot = self.db.execute(
            select(TokenSnapshot)
            .where(
                TokenSnapshot.chain_id == token.chain_id,
                TokenSnapshot.contract_address == token.contract_address,
            )
            .order_by(desc(TokenSnapshot.ts))
            .limit(1)
        ).scalar_one_or_none()

        return TokenCandidate(
            token=token,
            liquidity=latest_snapshot.liquidity if latest_snapshot else None,
            volume_24h=latest_snapshot.volume_24h if latest_snapshot else None,
        )

    def _select_best_candidate(self, candidates: list[TokenCandidate]) -> Token | None:
        liquidity_winner = self._unique_metric_winner(
            candidates,
            metric_name="liquidity",
        )
        if liquidity_winner is not None:
            return liquidity_winner

        volume_winner = self._unique_metric_winner(
            candidates,
            metric_name="volume_24h",
        )
        if volume_winner is not None:
            return volume_winner

        return None

    def _unique_metric_winner(
        self,
        candidates: list[TokenCandidate],
        *,
        metric_name: str,
    ) -> Token | None:
        metric_values = [
            candidate
            for candidate in candidates
            if getattr(candidate, metric_name) is not None
        ]
        if not metric_values:
            return None

        metric_values.sort(
            key=lambda candidate: (
                float(getattr(candidate, metric_name) or 0.0),
                float(candidate.volume_24h or 0.0),
                float(candidate.liquidity or 0.0),
            ),
            reverse=True,
        )

        winner = metric_values[0]
        winner_value = getattr(winner, metric_name)
        top_matches = [
            candidate
            for candidate in metric_values
            if getattr(candidate, metric_name) == winner_value
        ]

        if len(top_matches) == 1:
            return winner.token

        if metric_name != "volume_24h":
            return self._unique_metric_winner(top_matches, metric_name="volume_24h")

        return None

    def _normalize_symbol(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    def _unresolved_confidence(self, mention_type: str, chain_hint: str | None) -> float:
        if mention_type == "contract_address":
            return 0.4 if chain_hint else 0.35
        if mention_type == "cashtag":
            return 0.3
        if mention_type == "symbol_text":
            return 0.25
        return 0.2
