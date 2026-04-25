from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ChainOption, TokenListItem, TokenListResponse
from app.services.api_views import (
    build_token_detail_payload,
    build_trending_token_payload,
    fetch_token_rows,
)
from app.services.market_ingestion import SUPPORTED_CHAINS, build_chain_option

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("", response_model=TokenListResponse)
def list_tokens(
    chain_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> TokenListResponse:
    items = [TokenListItem(**row) for row in fetch_token_rows(db, chain_id=chain_id, limit=limit)]
    available_chains = [
        ChainOption(**build_chain_option(supported_chain_id))
        for supported_chain_id in SUPPORTED_CHAINS
    ]
    return TokenListResponse(items=items, available_chains=available_chains)


@router.get("/trending")
def get_trending_tokens(
    chain_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    return build_trending_token_payload(db, chain_id=chain_id, limit=limit)


@router.get("/{chain_id}/{contract_address}")
def get_token_detail(
    chain_id: str,
    contract_address: str,
    db: Session = Depends(get_db),
) -> dict:
    payload = build_token_detail_payload(
        db,
        chain_id=chain_id,
        contract_address=contract_address,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="Token not found.")
    return payload
