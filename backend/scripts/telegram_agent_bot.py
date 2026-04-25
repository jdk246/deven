from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings


TELEGRAM_API_ROOT = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 3900


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Run an example Telegram bot client for the trust-trace agent API.",
    )
    parser.add_argument(
        "--bot-token",
        default=settings.telegram_bot_token,
        help="Telegram bot token. Defaults to TELEGRAM_BOT_TOKEN.",
    )
    parser.add_argument(
        "--api-base-url",
        default=settings.telegram_api_base_url,
        help="Base URL for the local trust-trace backend API.",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=settings.telegram_poll_timeout_seconds,
        help="Long-poll timeout in seconds for Telegram getUpdates.",
    )
    return parser.parse_args()


def telegram_request(bot_token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{TELEGRAM_API_ROOT}/bot{bot_token}/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=payload.get("timeout", 30) + 10) as response:
        return json.loads(response.read().decode("utf-8"))


def call_agent_api(api_base_url: str, message: str) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/api/agent/query"
    body = json.dumps({"message": message, "debug": False}).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def compact_evidence(evidence_used: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in evidence_used[:3]:
        label = str(item.get("type") or "evidence")
        if item.get("top_results"):
            top_results = item["top_results"]
            if isinstance(top_results, list):
                detail = ", ".join(str(value) for value in top_results[:2])
            else:
                detail = str(top_results)
        elif item.get("token"):
            detail = str(item["token"])
        elif item.get("match_count") is not None:
            detail = f"matches={item['match_count']}"
        elif item.get("risk_level_enum"):
            detail = f"risk={item['risk_level_enum']}"
        elif item.get("attention_score") is not None:
            detail = f"attention_score={item['attention_score']}"
        else:
            detail = str(item.get("status") or "ok")
        lines.append(f"- {label}: {detail}")
    return lines


def render_reply(payload: dict[str, Any]) -> str:
    answer = str(payload.get("answer") or "I could not produce an answer.")
    disclaimer = str(payload.get("disclaimer") or "")
    evidence_used = payload.get("evidence_used")
    evidence_lines = compact_evidence(evidence_used if isinstance(evidence_used, list) else [])

    parts = [answer]
    if evidence_lines:
        parts.extend(["", "Evidence:"])
        parts.extend(evidence_lines)
    if disclaimer:
        parts.extend(["", disclaimer])

    text = "\n".join(parts).strip()
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text

    trimmed_answer = answer[: MAX_MESSAGE_LENGTH - len(disclaimer) - 32].rstrip()
    return f"{trimmed_answer}\n\n{disclaimer}".strip()


def help_text() -> str:
    return (
        "Send a token or market-research question and this bot will call the local "
        "trust-trace agent API for an answer.\n\n"
        "Examples:\n"
        "- Which tokens are trending right now?\n"
        "- Why is BNB trending?\n"
        "- Which tokens look risky?\n"
        "- Which KOLs mentioned SOL?"
    )


def handle_message(bot_token: str, api_base_url: str, message: dict[str, Any]) -> None:
    chat = message.get("chat") if isinstance(message, dict) else None
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    text = message.get("text") if isinstance(message, dict) else None
    if chat_id is None or not isinstance(text, str):
        return

    stripped = text.strip()
    if not stripped:
        return

    if stripped in {"/start", "/help"}:
        reply = help_text()
    else:
        try:
            payload = call_agent_api(api_base_url, stripped)
            reply = render_reply(payload)
        except error.HTTPError as exc:
            reply = f"Backend API returned HTTP {exc.code}. Please check the local service."
        except Exception as exc:
            reply = f"Backend API call failed: {exc}"

    telegram_request(
        bot_token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": reply,
        },
    )


def run_bot(bot_token: str, api_base_url: str, poll_timeout: int) -> None:
    offset: int | None = None
    print(f"Telegram bot is polling. backend_api={api_base_url.rstrip('/')}/api/agent/query")
    print("Press Ctrl+C to stop.")

    while True:
        payload: dict[str, Any] = {"timeout": poll_timeout}
        if offset is not None:
            payload["offset"] = offset

        response = telegram_request(bot_token, "getUpdates", payload)
        updates = response.get("result")
        if not isinstance(updates, list):
            time.sleep(1)
            continue

        for update in updates:
            if not isinstance(update, dict):
                continue
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                offset = update_id + 1
            message = update.get("message") or update.get("edited_message")
            if isinstance(message, dict):
                handle_message(bot_token, api_base_url, message)


def main() -> int:
    args = parse_args()
    if not args.bot_token:
        print("TELEGRAM_BOT_TOKEN is required to run the Telegram example client.", file=sys.stderr)
        return 1

    try:
        run_bot(
            bot_token=str(args.bot_token),
            api_base_url=str(args.api_base_url),
            poll_timeout=max(1, int(args.poll_timeout)),
        )
    except KeyboardInterrupt:
        print("\nStopped Telegram bot.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
