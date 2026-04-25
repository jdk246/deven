from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.api_views import (
    build_kol_detail_payload,
    build_kol_feed_payload,
    build_kol_list_payload,
)
from app.services.kol_performance import KOLPerformanceService

router = APIRouter(prefix="/api/kols", tags=["kols"])


@router.get("")
def list_kols(db: Session = Depends(get_db)) -> dict:
    return build_kol_list_payload(db)


@router.get("/feed")
def get_kol_feed(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    return build_kol_feed_payload(db, limit=limit)


@router.get("/rankings")
def get_kol_rankings(
    limit: int = Query(default=20, ge=1, le=100),
    min_evaluated_calls: int | None = Query(default=None, ge=0, le=10_000),
    include_insufficient: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> dict:
    return KOLPerformanceService(db).list_rankings(
        limit=limit,
        min_evaluated_calls=min_evaluated_calls,
        include_insufficient=include_insufficient,
    )


@router.get("/{handle}/track-record")
def get_kol_track_record(handle: str, db: Session = Depends(get_db)) -> dict:
    payload = KOLPerformanceService(db).get_track_record(handle=handle)
    if payload is None:
        raise HTTPException(status_code=404, detail="KOL not found.")
    return payload


@router.get("/{handle}")
def get_kol_detail(handle: str, db: Session = Depends(get_db)) -> dict:
    payload = build_kol_detail_payload(db, handle=handle)
    if payload is None:
        raise HTTPException(status_code=404, detail="KOL not found.")
    return payload
