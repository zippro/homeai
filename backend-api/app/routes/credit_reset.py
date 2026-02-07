from __future__ import annotations

from fastapi import APIRouter, Query

from app.credit_reset_store import (
    get_credit_reset_schedule,
    run_daily_credit_reset,
    tick_daily_credit_reset,
    update_credit_reset_schedule,
)
from app.schemas import (
    CreditResetRunResponse,
    CreditResetScheduleResponse,
    CreditResetScheduleUpdateRequest,
    CreditResetTickResponse,
)

router = APIRouter(prefix="/v1/admin/credits", tags=["admin", "credits"])


@router.get("/reset-schedule", response_model=CreditResetScheduleResponse)
async def get_reset_schedule() -> CreditResetScheduleResponse:
    return get_credit_reset_schedule()


@router.put("/reset-schedule", response_model=CreditResetScheduleResponse)
async def put_reset_schedule(payload: CreditResetScheduleUpdateRequest) -> CreditResetScheduleResponse:
    return update_credit_reset_schedule(payload)


@router.post("/run-daily-reset", response_model=CreditResetRunResponse)
async def run_reset(dry_run: bool = Query(default=False)) -> CreditResetRunResponse:
    return run_daily_credit_reset(dry_run=dry_run)


@router.post("/tick-reset", response_model=CreditResetTickResponse)
async def tick_reset() -> CreditResetTickResponse:
    return tick_daily_credit_reset()
