from __future__ import annotations

import asyncio
from copy import deepcopy
from unittest.mock import patch

from app.agent_tools.registry import ToolRegistry
from app.clients.binance_skills import BinanceSkillsResult
from app.services.insight_generation import InsightGenerationService
from app.services.kol_ingestion import KOLIngestionService
from app.services.kol_performance import KOLPerformanceService
from app.services.market_ingestion import MarketIngestionService
from tests.helpers import make_agent_tool_result


FAKE_MARKET_DATA = {
    "56": [
        {
            "contract_address": "0x5600000000000000000000000000000000000001",
            "symbol": "BNB",
            "name": "BNB",
            "price": 650.0,
            "percent_change_24h": 4.1,
            "volume_24h": 2_500_000.0,
            "liquidity": 1_900_000.0,
            "holders": 40_000,
            "top10_holders_pct": 0.24,
            "smart_money_holding_pct": 0.08,
            "risk_level_enum": "LOW",
            "risk_level": 8,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
        {
            "contract_address": "0x5600000000000000000000000000000000000002",
            "symbol": "CAKE",
            "name": "PancakeSwap",
            "price": 2.15,
            "percent_change_24h": 7.3,
            "volume_24h": 1_350_000.0,
            "liquidity": 820_000.0,
            "holders": 18_000,
            "top10_holders_pct": 0.31,
            "smart_money_holding_pct": 0.05,
            "risk_level_enum": "LOW",
            "risk_level": 10,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
        {
            "contract_address": "0x5600000000000000000000000000000000000003",
            "symbol": "LISTA",
            "name": "Lista DAO",
            "price": 0.68,
            "percent_change_24h": 9.4,
            "volume_24h": 980_000.0,
            "liquidity": 450_000.0,
            "holders": 9_500,
            "top10_holders_pct": 0.42,
            "smart_money_holding_pct": 0.04,
            "risk_level_enum": "LOW",
            "risk_level": 12,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
        {
            "contract_address": "0x5600000000000000000000000000000000000004",
            "symbol": "MUBARAK",
            "name": "Mubarak",
            "price": 0.11,
            "percent_change_24h": 12.1,
            "volume_24h": 760_000.0,
            "liquidity": 210_000.0,
            "holders": 5_400,
            "top10_holders_pct": 0.54,
            "smart_money_holding_pct": 0.03,
            "risk_level_enum": "MEDIUM",
            "risk_level": 45,
            "buy_tax": 0.02,
            "sell_tax": 0.03,
            "is_verified": True,
        },
        {
            "contract_address": "0x5600000000000000000000000000000000000005",
            "symbol": "TST",
            "name": "Trust Starter",
            "price": 0.045,
            "percent_change_24h": 14.8,
            "volume_24h": 540_000.0,
            "liquidity": 160_000.0,
            "holders": 3_900,
            "top10_holders_pct": 0.58,
            "smart_money_holding_pct": 0.02,
            "risk_level_enum": "MEDIUM",
            "risk_level": 48,
            "buy_tax": 0.03,
            "sell_tax": 0.03,
            "is_verified": True,
        },
    ],
    "CT_501": [
        {
            "contract_address": "So11111111111111111111111111111111111111112",
            "symbol": "SOL",
            "name": "Solana",
            "price": 155.0,
            "percent_change_24h": 5.6,
            "volume_24h": 2_100_000.0,
            "liquidity": 1_250_000.0,
            "holders": 31_000,
            "top10_holders_pct": 0.27,
            "smart_money_holding_pct": 0.07,
            "risk_level_enum": "LOW",
            "risk_level": 7,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
        {
            "contract_address": "So22222222222222222222222222222222222222222",
            "symbol": "BONK",
            "name": "Bonk",
            "price": 0.000032,
            "percent_change_24h": 11.2,
            "volume_24h": 1_450_000.0,
            "liquidity": 600_000.0,
            "holders": 22_000,
            "top10_holders_pct": 0.39,
            "smart_money_holding_pct": 0.05,
            "risk_level_enum": "LOW",
            "risk_level": 14,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
        {
            "contract_address": "So33333333333333333333333333333333333333333",
            "symbol": "WIF",
            "name": "dogwifhat",
            "price": 2.78,
            "percent_change_24h": 13.8,
            "volume_24h": 1_700_000.0,
            "liquidity": 770_000.0,
            "holders": 14_500,
            "top10_holders_pct": 0.36,
            "smart_money_holding_pct": 0.06,
            "risk_level_enum": "LOW",
            "risk_level": 16,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
        {
            "contract_address": "So44444444444444444444444444444444444444444",
            "symbol": "PEPE",
            "name": "Pepe Sol",
            "price": 0.0000048,
            "percent_change_24h": 8.9,
            "volume_24h": 640_000.0,
            "liquidity": 180_000.0,
            "holders": 4_200,
            "top10_holders_pct": 0.61,
            "smart_money_holding_pct": 0.03,
            "risk_level_enum": "MEDIUM",
            "risk_level": 40,
            "buy_tax": 0.02,
            "sell_tax": 0.02,
            "is_verified": True,
        },
        {
            "contract_address": "So55555555555555555555555555555555555555555",
            "symbol": "FET",
            "name": "Fetch AI Sol",
            "price": 1.64,
            "percent_change_24h": 6.7,
            "volume_24h": 520_000.0,
            "liquidity": 220_000.0,
            "holders": 5_600,
            "top10_holders_pct": 0.44,
            "smart_money_holding_pct": 0.03,
            "risk_level_enum": "LOW",
            "risk_level": 18,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "is_verified": True,
        },
    ],
}


class FakeBinanceSkillsClient:
    def _find_token(self, chain_id: str, contract_address: str) -> dict:
        for token in FAKE_MARKET_DATA.get(chain_id, []):
            if token["contract_address"] == contract_address:
                return token
        raise KeyError(f"Unknown token {chain_id}:{contract_address}")

    async def get_trending_token_rank(self, *, chain_id: str | None = None, size: int = 100, **_: object) -> BinanceSkillsResult:
        rows = []
        for selected_chain in ([chain_id] if chain_id else FAKE_MARKET_DATA):
            for token in FAKE_MARKET_DATA.get(selected_chain, []):
                rows.append(
                    {
                        "chainId": selected_chain,
                        "contractAddress": token["contract_address"],
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "icon": f"https://example.com/{token['symbol'].lower()}.png",
                    }
                )
        rows = rows[:size]
        return BinanceSkillsResult(data=deepcopy(rows), raw={"data": deepcopy(rows)})

    async def get_token_metadata(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        token = self._find_token(chain_id, contract_address)
        payload = {
            "chainId": chain_id,
            "contractAddress": contract_address,
            "symbol": token["symbol"],
            "name": token["name"],
            "decimals": 18 if chain_id == "56" else 9,
            "icon": f"https://example.com/{token['symbol'].lower()}.png",
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_token_dynamic_data(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        token = self._find_token(chain_id, contract_address)
        payload = {
            "price": token["price"],
            "percentChange24h": token["percent_change_24h"],
            "volume24h": token["volume_24h"],
            "liquidity": token["liquidity"],
            "marketCap": token["volume_24h"] * 2.5,
            "fdv": token["volume_24h"] * 3.1,
            "holders": token["holders"],
            "top10HoldersPercentage": token["top10_holders_pct"],
            "smartMoneyHoldingPercent": token["smart_money_holding_pct"],
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_token_dynamic_market_data(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        return await self.get_token_dynamic_data(chain_id, contract_address)

    async def get_token_audit(self, chain_id: str, contract_address: str) -> BinanceSkillsResult:
        token = self._find_token(chain_id, contract_address)
        payload = {
            "hasResult": True,
            "isSupported": True,
            "riskLevelEnum": token["risk_level_enum"],
            "riskLevel": token["risk_level"],
            "extraInfo": {
                "buyTax": token["buy_tax"],
                "sellTax": token["sell_tax"],
                "isVerified": token["is_verified"],
            },
            "riskItems": [],
        }
        return BinanceSkillsResult(data=payload, raw={"data": payload})

    async def get_smart_money_signals(self, chain_id: str, *, page_size: int = 100, **_: object) -> BinanceSkillsResult:
        rows = []
        for index, token in enumerate(FAKE_MARKET_DATA.get(chain_id, [])[:page_size], start=1):
            rows.append(
                {
                    "signalId": f"{chain_id}-signal-{index}",
                    "chainId": chain_id,
                    "contractAddress": token["contract_address"],
                    "ticker": token["symbol"],
                    "direction": "buy" if index % 2 else "accumulate",
                    "smartMoneyCount": 2 + index,
                    "signalTriggerTime": 1_710_000_000_000 + index * 60_000,
                    "totalTokenValue": token["volume_24h"] / 4,
                    "alertPrice": token["price"] * 0.95,
                    "currentPrice": token["price"],
                    "highestPrice": token["price"] * 1.12,
                    "exitRate": 0.15,
                    "status": "open",
                    "maxGain": 16.0 + index,
                }
            )
        return BinanceSkillsResult(data=rows, raw={"data": rows})

    async def get_smart_money_inflow_rank(self, chain_id: str, **_: object) -> BinanceSkillsResult:
        rows = [
            {
                "chainId": chain_id,
                "contractAddress": token["contract_address"],
                "symbol": token["symbol"],
            }
            for token in FAKE_MARKET_DATA.get(chain_id, [])
        ]
        return BinanceSkillsResult(data=rows, raw={"data": rows})


def _make_live_tool_result(tool_name: str, input_args: dict, data: dict) -> object:
    skill_name = {
        "crypto_market_rank": "crypto_market_rank",
        "query_token_info": "query_token_info",
        "query_token_audit": "query_token_audit",
        "trading_signal": "trading_signal",
    }.get(tool_name, tool_name)
    return make_agent_tool_result(
        skill_name=skill_name,
        tool_name=tool_name if tool_name != "query_token_info" else "token_info_bundle",
        source="binance_skills",
        input_args=input_args,
        data=data,
    )


def test_backend_e2e_smoke_without_internet(db_session, api_client) -> None:
    fake_client = FakeBinanceSkillsClient()
    market_service = MarketIngestionService(db=db_session, binance_client=fake_client)
    market_summary = asyncio.run(
        market_service.run_refresh(
            jobs=["market", "audits", "smart_money"],
            chains=["56", "CT_501"],
            limit_per_chain=5,
        )
    )
    kol_summary = KOLIngestionService(db_session).run_refresh()
    insight_summary = InsightGenerationService(db_session).generate_all_insights(
        chains=["56", "CT_501"],
        limit_per_chain=5,
        persist=True,
    )
    kol_performance_summary = KOLPerformanceService(db_session).refresh_kol_performance()

    assert market_summary["status"] == "ok"
    assert kol_summary["profiles_seen"] >= 20
    assert insight_summary["insights_created"] >= 5
    assert "calls_created" in kol_performance_summary

    original_call_tool = ToolRegistry.call_tool

    async def patched_call_tool(self, tool_name: str, input_args: dict | None = None):
        args = input_args or {}
        if tool_name == "query_token_info":
            token = fake_client._find_token(args["chain_id"], args["contract_address"])
            return _make_live_tool_result(
                tool_name,
                args,
                {
                    "metadata": {"symbol": token["symbol"], "name": token["name"]},
                    "dynamic_market_data": {
                        "price": token["price"],
                        "percentChange24h": token["percent_change_24h"],
                        "volume24h": token["volume_24h"],
                        "liquidity": token["liquidity"],
                    },
                },
            )
        if tool_name == "query_token_audit":
            token = fake_client._find_token(args["chain_id"], args["contract_address"])
            return _make_live_tool_result(
                tool_name,
                args,
                {
                    "riskLevelEnum": token["risk_level_enum"],
                    "extraInfo": {
                        "buyTax": token["buy_tax"],
                        "sellTax": token["sell_tax"],
                        "isVerified": token["is_verified"],
                    },
                },
            )
        return await original_call_tool(self, tool_name, args)

    with patch.object(ToolRegistry, "call_tool", new=patched_call_tool):
        health_response = api_client.get("/health")
        agent_health_response = api_client.get("/api/agent/health")
        tools_response = api_client.get("/api/agent/tools")
        validate_response = api_client.get("/api/admin/validate")
        chat_response = api_client.post(
            "/api/agent/query",
            json={"message": "Why is BNB trending?", "chain_id": "56", "debug": True},
        )
        kols_response = api_client.get("/api/kols")
        rankings_response = api_client.get("/api/kols/rankings")
        insights_response = api_client.get("/api/insights?limit=10")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    assert agent_health_response.status_code == 200
    assert agent_health_response.json()["status"] == "ok"

    tools_payload = tools_response.json()
    assert tools_response.status_code == 200
    assert len(tools_payload["items"]) >= 15

    validation_payload = validate_response.json()
    assert validate_response.status_code == 200
    assert validation_payload["status"] in {"pass", "warn"}
    assert len(validation_payload["checks"]) == 14

    chat_payload = chat_response.json()
    assert chat_response.status_code == 200
    assert set(chat_payload) == {"answer", "evidence_used", "missing_data", "tool_trace", "disclaimer"}
    assert chat_payload["tool_trace"]

    kols_payload = kols_response.json()
    assert kols_response.status_code == 200
    assert len(kols_payload["items"]) >= 20

    rankings_payload = rankings_response.json()
    assert rankings_response.status_code == 200
    assert "items" in rankings_payload
    assert "methodology" in rankings_payload

    insights_payload = insights_response.json()
    assert insights_response.status_code == 200
    assert len(insights_payload["items"]) >= 5
