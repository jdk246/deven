from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.api_views import build_insight_list_payload

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
def list_insights(
    chain_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    return build_insight_list_payload(db, chain_id=chain_id, limit=limit)
