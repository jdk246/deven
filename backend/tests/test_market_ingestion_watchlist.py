from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.clients.binance_skills import BinanceSkillsResult
from app.models import Token, TokenAudit, TokenSnapshot
from app.services.market_ingestion import MarketIngestionService


WATCHLIST_TOKEN_DATA = {
    ("56", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"): {
        "binance_symbol": "WBNB",
        "binance_name": "Wrapped BNB",
        "expected_symbol": "BNB",
        "expected_name": "BNB",
        "price": 689.42,
        "volume_24h": 12_450_000.0,
        "liquidity": 8_250_000.0,
        "holders": 52_000,
        "risk_level_enum": "LOW",
        "risk_level": 8,
    },
    ("56", "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"): {
        "binance_symbol": "BSC_ETH",
        "binance_name": "BSC Ether",
        "expected_symbol": "ETH",
        "expected_name": "Ethereum",
        "price": 3_281.55,
        "volume_24h": 9_840_000.0,
        "liquidity": 5_340_000.0,
        "holders": 41_500,
        "risk_level_enum": "LOW",
        "risk_level": 6,
    },
    ("56", "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"): {
        "binance_symbol": "BTCB",
        "binance_name": "BTCB Token",
        "expected_symbol": "BTC",
        "expected_name": "Bitcoin",
        "price": 94_210.11,
        "volume_24h": 14_260_000.0,
        "liquidity": 9_100_000.0,
        "holders": 36_200,
        "risk_level_enum": "LOW",
        "risk_level": 5,
    },
    ("CT_501", "So11111111111111111111111111111111111111112"): {
        "binance_symbol": "WSOL",
        "binance_name": "Wrapped SOL",
        "expected_symbol": "SOL",
        "expected_name": "Solana",
        "price": 182.73,
        "volume_24h": 8_120_000.0,
        "liquidity": 4_880_000.0,
        "holders": 61_400,
        "risk_level_enum": "LOW",
        "risk_level": 7,
    },
}


class WatchlistOnlyBinanceClient:
    async def get_trending_token_rank(
        self,
        *,
        chain_id: str | None = None,
        size: int = 100,
        **_: object,
    ) -> BinanceSkillsResult:
        rows: list[dict[str, str]] = []
        if chain_id == "56":
            rows.append(
                {
                    "chainId": "56",
                    "contractAddress": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
                    "symbol": "WBNB",
                    "name": "Wrapped BNB",
                }
            )
        return BinanceSkillsResult(data=rows[:size], raw={"data": rows[:size]})

    async def get_token_metadata(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        token = WATCHLIST_TOKEN_DATA[(chain_id, contract_address)]
        payload = {
            "chainId": chain_id,
            "contractAddress": contract_address,
            "symbol": token["binance_symbol"],
            "name": token["binance_name"],
            "decimals": 18 if chain_id == "56" else 9,
            "icon": f"https://example.com/{token['expected_symbol'].lower()}.png",
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_token_dynamic_data(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        token = WATCHLIST_TOKEN_DATA[(chain_id, contract_address)]
        payload = {
            "price": token["price"],
            "percentChange24h": 3.2,
            "volume24h": token["volume_24h"],
            "liquidity": token["liquidity"],
            "marketCap": token["volume_24h"] * 2.2,
            "fdv": token["volume_24h"] * 2.7,
            "holders": token["holders"],
            "top10HoldersPercentage": 0.18,
            "smartMoneyHoldingPercent": 0.06,
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_token_dynamic_market_data(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        return await self.get_token_dynamic_data(chain_id, contract_address)

    async def get_token_audit(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        token = WATCHLIST_TOKEN_DATA[(chain_id, contract_address)]
        payload = {
            "hasResult": True,
            "isSupported": True,
            "riskLevelEnum": token["risk_level_enum"],
            "riskLevel": token["risk_level"],
            "extraInfo": {
                "buyTax": 0.0,
                "sellTax": 0.0,
                "isVerified": True,
            },
            "riskItems": [],
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_smart_money_signals(self, chain_id: str, **_: object) -> BinanceSkillsResult:
        return BinanceSkillsResult(data=[], raw={"data": []})


def test_market_refresh_adds_curated_major_watchlist_tokens(db_session) -> None:
    service = MarketIngestionService(
        db=db_session,
        binance_client=WatchlistOnlyBinanceClient(),
    )

    summary = asyncio.run(
        service.run_refresh(
            jobs=["market", "audits"],
            chains=["56", "CT_501"],
            limit_per_chain=5,
        )
    )

    assert summary["status"] == "ok"

    summary_by_chain = {item["chain_id"]: item for item in summary["summary"]}
    assert summary_by_chain["56"]["watchlist_targets"] == 3
    assert summary_by_chain["56"]["watchlist_upserted"] == 3
    assert summary_by_chain["CT_501"]["watchlist_targets"] == 1
    assert summary_by_chain["CT_501"]["watchlist_upserted"] == 1

    for (chain_id, contract_address), expected in WATCHLIST_TOKEN_DATA.items():
        token = db_session.get(Token, (chain_id, contract_address))
        assert token is not None
        assert token.symbol == expected["expected_symbol"]
        assert token.name == expected["expected_name"]

        snapshot = db_session.execute(
            select(TokenSnapshot).where(
                TokenSnapshot.chain_id == chain_id,
                TokenSnapshot.contract_address == contract_address,
            )
        ).scalar_one_or_none()
        assert snapshot is not None
        assert snapshot.price == expected["price"]

        audit = db_session.execute(
            select(TokenAudit).where(
                TokenAudit.chain_id == chain_id,
                TokenAudit.contract_address == contract_address,
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.risk_level_enum == expected["risk_level_enum"]
