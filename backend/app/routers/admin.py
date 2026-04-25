from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clients import BinanceSkillsClient
from app.db import get_db
from app.schemas import AdminRefreshRequest, AdminRefreshResponse, BackendValidationResponse
from app.services.backend_validation import BackendValidationService
from app.services.insight_generation import InsightGenerationService
from app.services.kol_ingestion import KOLIngestionService
from app.services.market_ingestion import (
    SUPPORTED_CHAINS,
    MarketIngestionService,
    build_chain_option,
    get_enabled_chain_ids,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

MARKET_REFRESH_JOBS = {"market", "audits", "smart_money"}


@router.post("/refresh", response_model=AdminRefreshResponse)
async def refresh_market(
    payload: AdminRefreshRequest,
    db: Session = Depends(get_db),
) -> AdminRefreshResponse:
    requested_jobs = list(dict.fromkeys(payload.jobs))
    market_jobs = [job for job in requested_jobs if job in MARKET_REFRESH_JOBS]
    should_run_kols = "kols" in requested_jobs
    should_run_insights = "insights" in requested_jobs

    if market_jobs:
        async with BinanceSkillsClient() as binance_client:
            service = MarketIngestionService(db=db, binance_client=binance_client)
            result = await service.run_refresh(
                jobs=market_jobs,
                chains=payload.chains,
                limit_per_chain=payload.limit_per_chain,
            )
    else:
        result = _build_empty_refresh_response(payload)

    result["jobs"] = [
        job for job in requested_jobs if job in MARKET_REFRESH_JOBS or job in {"kols", "insights"}
    ]

    if should_run_kols:
        kol_service = KOLIngestionService(db=db)
        result["kol_summary"] = kol_service.run_refresh()

    if should_run_insights:
        insight_service = InsightGenerationService(db=db)
        result["insight_summary"] = insight_service.generate_all_insights(
            chains=payload.chains,
            limit_per_chain=payload.limit_per_chain,
        )

    return AdminRefreshResponse(**result)


@router.get("/validate", response_model=BackendValidationResponse)
def validate_backend(db: Session = Depends(get_db)) -> BackendValidationResponse:
    return BackendValidationService(db).validate()


def _build_empty_refresh_response(payload: AdminRefreshRequest) -> dict[str, object]:
    requested_chains = list(payload.chains or get_enabled_chain_ids())
    selected_chains = [chain_id for chain_id in requested_chains if chain_id in SUPPORTED_CHAINS]

    if not selected_chains:
        selected_chains = get_enabled_chain_ids()

    ignored_chains = [
        chain_id for chain_id in requested_chains if chain_id not in SUPPORTED_CHAINS
    ]
    clamped_limit = max(1, min(payload.limit_per_chain, 100))

    result: dict[str, object] = {
        "status": "ok",
        "jobs": [],
        "chains": [build_chain_option(chain_id) for chain_id in selected_chains],
        "limit_per_chain": clamped_limit,
        "summary": [],
        "errors": [],
    }

    if ignored_chains:
        result["errors"] = [f"Ignored unsupported chains: {', '.join(ignored_chains)}"]

    return result
