from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AgentQueryRequest, AgentQueryResponse
from app.services.openai_agent import get_agent_service

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=AgentQueryResponse)
def chat(payload: AgentQueryRequest, db: Session = Depends(get_db)) -> AgentQueryResponse:
    response = get_agent_service(db).answer_question(
        message=payload.message,
        chain_id=payload.chain_id,
        token_context=payload.token_context.model_dump(exclude_none=True) if payload.token_context else None,
        debug=payload.debug,
    )
    return AgentQueryResponse(**response)
