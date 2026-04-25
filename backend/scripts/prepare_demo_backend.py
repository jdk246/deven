from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.clients import BinanceSkillsClient
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.services.backend_validation import BackendValidationService
from app.services.insight_generation import InsightGenerationService
from app.services.kol_ingestion import KOLIngestionService
from app.services.kol_performance import KOLPerformanceService
from app.services.market_ingestion import MarketIngestionService, get_enabled_chain_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the trust-trace backend database for a local demo run.",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip live Binance market ingestion and only run local seed-backed setup.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Drop and recreate all configured database tables before preparing demo data.",
    )
    parser.add_argument(
        "--limit-per-chain",
        type=int,
        default=20,
        help="Maximum number of tokens to ingest and score per enabled chain.",
    )
    return parser.parse_args()


def print_section(title: str) -> None:
    print()
    print(f"== {title} ==")


def print_json(label: str, payload: Any) -> None:
    print(f"{label}:")
    print(json.dumps(payload, indent=2, default=str))


def print_validation_report(payload: Any) -> None:
    print("Validation checks:")
    for check in payload.checks:
        print(
            f"- {check.name}: {check.status} "
            f"(expected {check.expected}, actual {check.actual})"
        )
        print(f"  fix_hint: {check.fix_hint}")


async def run_market_refresh(db, limit_per_chain: int) -> dict[str, Any]:
    async with BinanceSkillsClient() as client:
        service = MarketIngestionService(db=db, binance_client=client)
        return await service.run_refresh(
            jobs=["market", "audits", "smart_money"],
            chains=get_enabled_chain_ids(),
            limit_per_chain=limit_per_chain,
        )


def main() -> int:
    args = parse_args()
    settings = get_settings()
    limit_per_chain = max(1, min(int(args.limit_per_chain), 100))

    print_section("Backend Demo Prep")
    print(f"database_url: {settings.database_url}")
    print(f"enabled_chains: {', '.join(get_enabled_chain_ids())}")
    print(f"kol_data_mode: {settings.kol_data_mode}")
    print(f"skip_network: {args.skip_network}")
    print(f"reset_db: {args.reset_db}")

    if args.reset_db:
        print_section("Reset Database")
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables.")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print_section("Seed KOL Ingestion")
        seed_summary = KOLIngestionService(db).run_refresh()
        print_json("seed_kol_summary", seed_summary)

        if args.skip_network:
            print_section("Market Ingestion")
            print("Skipping live Binance ingestion because --skip-network was set.")
            market_summary: dict[str, Any] | None = None
        else:
            print_section("Market Ingestion")
            try:
                market_summary = asyncio.run(run_market_refresh(db, limit_per_chain))
                print_json("market_summary", market_summary)
            except Exception as exc:
                market_summary = {"status": "error", "errors": [str(exc)]}
                print_json("market_summary", market_summary)

            print_section("Mention Remap Refresh")
            remap_summary = KOLIngestionService(db).run_refresh()
            print_json("remap_kol_summary", remap_summary)

        print_section("Insight Generation")
        insight_summary = InsightGenerationService(db).generate_all_insights(
            chains=get_enabled_chain_ids(),
            limit_per_chain=limit_per_chain,
            persist=True,
        )
        print_json("insight_summary", insight_summary)

        print_section("KOL Performance Refresh")
        kol_performance_summary = KOLPerformanceService(db).refresh_kol_performance()
        print_json("kol_performance_summary", kol_performance_summary)

        rankings = KOLPerformanceService(db).list_rankings(
            limit=5,
            include_insufficient=True,
        )
        top_rankings = rankings.get("items") if isinstance(rankings, dict) else []
        if top_rankings:
            print("Top 5 KOL rankings:")
            for item in top_rankings[:5]:
                print(
                    "- "
                    f"@{item.get('handle')} | "
                    f"{item.get('label')} | "
                    f"score={item.get('track_record_score')} | "
                    f"evaluated_calls={item.get('evaluated_calls')}"
                )
        else:
            print("Top 5 KOL rankings:")
            print("- No ranking rows available yet.")

        print_section("Validation")
        validation = BackendValidationService(db).validate()
        print(f"overall_status: {validation.status}")
        print_validation_report(validation)
        return 0 if validation.status in {"pass", "warn"} else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
