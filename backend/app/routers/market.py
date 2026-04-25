from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ChainOption, TokenListItem, TokenListResponse
from app.services.market_ingestion import SUPPORTED_CHAINS, build_chain_option, fetch_token_rows

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/tokens", response_model=TokenListResponse)
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
