from __future__ import annotations

from dataclasses import dataclass
from typing import Final


BULLISH_TERMS: Final[tuple[str, ...]] = (
    "accumulate",
    "adding",
    "breakout",
    "bullish",
    "cleaner read",
    "conviction",
    "follow-through",
    "higher high",
    "long",
    "momentum",
    "reload",
    "reloading",
    "rotation",
    "strength",
    "support holding",
    "uptrend",
    "watching",
)

BEARISH_TERMS: Final[tuple[str, ...]] = (
    "avoid",
    "bearish",
    "breakdown",
    "caution",
    "crack",
    "distribution",
    "dump",
    "exit",
    "fade",
    "fading",
    "lower low",
    "mixed",
    "not trust",
    "risk",
    "rug",
    "sell",
    "skeptical",
    "unlock pain",
    "weakness",
)

NEUTRAL_SENTIMENT = "neutral"
UNKNOWN_SENTIMENT = "unknown"


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float
    bullish_hits: int
    bearish_hits: int


class RuleBasedSentimentClassifier:
    def __init__(
        self,
        *,
        bullish_terms: tuple[str, ...] = BULLISH_TERMS,
        bearish_terms: tuple[str, ...] = BEARISH_TERMS,
    ) -> None:
        self.bullish_terms = tuple(term.casefold() for term in bullish_terms)
        self.bearish_terms = tuple(term.casefold() for term in bearish_terms)

    def classify(self, text: str | None) -> SentimentResult:
        normalized = self._normalize_text(text)
        if normalized is None:
            return SentimentResult(
                label=UNKNOWN_SENTIMENT,
                score=0.0,
                bullish_hits=0,
                bearish_hits=0,
            )

        bullish_hits = self._count_hits(normalized, self.bullish_terms)
        bearish_hits = self._count_hits(normalized, self.bearish_terms)
        score = self._score(bullish_hits, bearish_hits)

        if bullish_hits > bearish_hits:
            label = "bullish"
        elif bearish_hits > bullish_hits:
            label = "bearish"
        else:
            label = NEUTRAL_SENTIMENT

        return SentimentResult(
            label=label,
            score=score,
            bullish_hits=bullish_hits,
            bearish_hits=bearish_hits,
        )

    def _normalize_text(self, text: str | None) -> str | None:
        if text is None:
            return None

        normalized = " ".join(text.casefold().split())
        return normalized or None

    def _count_hits(self, text: str, keywords: tuple[str, ...]) -> int:
        hits = 0
        for keyword in keywords:
            if keyword in text:
                hits += 1
        return hits

    def _score(self, bullish_hits: int, bearish_hits: int) -> float:
        total_hits = bullish_hits + bearish_hits
        if total_hits == 0:
            return 0.0

        raw_score = (bullish_hits - bearish_hits) / total_hits
        return max(-1.0, min(1.0, round(raw_score, 3)))
