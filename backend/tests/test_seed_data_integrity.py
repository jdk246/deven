from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
KOLS_PATH = DATA_DIR / "kols.yaml"
POSTS_PATH = DATA_DIR / "kol_posts_seed.json"


def test_kols_yaml_exists_and_has_required_fields() -> None:
    assert KOLS_PATH.exists(), f"Missing seed KOL file: {KOLS_PATH}"

    payload = yaml.safe_load(KOLS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 20

    for row in payload:
        assert isinstance(row, dict)
        assert row.get("handle")
        assert row.get("display_name")
        assert row.get("category")
        assert row.get("priority") is not None


def test_kol_posts_seed_json_exists_and_has_required_fields() -> None:
    assert POSTS_PATH.exists(), f"Missing seed post file: {POSTS_PATH}"

    payload = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 40

    required_fields = {
        "handle",
        "created_at",
        "text",
        "url",
        "like_count",
        "repost_count",
        "reply_count",
        "view_count",
        "source_mode",
    }

    for row in payload:
        assert isinstance(row, dict)
        assert required_fields.issubset(row)
        assert row["source_mode"] == "seed"


def test_seed_posts_have_enough_cashtags_and_sentiment_words() -> None:
    payload = json.loads(POSTS_PATH.read_text(encoding="utf-8"))

    cashtag_posts = sum(
        1
        for row in payload
        if re.search(r"\$[A-Za-z][A-Za-z0-9]{1,14}\b", str(row.get("text", "")))
    )
    sentiment_posts = sum(
        1
        for row in payload
        if re.search(r"\b(bullish|bearish)\b", str(row.get("text", "")), re.IGNORECASE)
    )

    assert cashtag_posts >= 15
    assert sentiment_posts >= 5
