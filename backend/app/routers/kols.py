from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.api_views import build_kol_detail_payload, build_kol_list_payload

router = APIRouter(prefix="/api/kols", tags=["kols"])


@router.get("")
def list_kols(db: Session = Depends(get_db)) -> dict:
    return build_kol_list_payload(db)


@router.get("/{handle}")
def get_kol_detail(handle: str, db: Session = Depends(get_db)) -> dict:
    payload = build_kol_detail_payload(db, handle=handle)
    if payload is None:
        raise HTTPException(status_code=404, detail="KOL not found.")
    return payload
