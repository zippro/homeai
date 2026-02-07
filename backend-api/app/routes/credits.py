from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.credit_store import consume_credits, get_balance, grant_credits
from app.schemas import CreditBalanceResponse, CreditConsumeRequest, CreditGrantRequest, CreditOperationResponse

router = APIRouter(prefix="/v1/credits", tags=["credits"])


@router.get("/balance/{user_id}", response_model=CreditBalanceResponse)
async def credit_balance(user_id: str) -> CreditBalanceResponse:
    return get_balance(user_id)


@router.post("/consume", response_model=CreditOperationResponse)
async def credit_consume(payload: CreditConsumeRequest) -> CreditOperationResponse:
    try:
        return consume_credits(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/grant", response_model=CreditOperationResponse)
async def credit_grant(payload: CreditGrantRequest) -> CreditOperationResponse:
    try:
        return grant_credits(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
