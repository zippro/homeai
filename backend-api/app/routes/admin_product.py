from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.product_store import (
    delete_plan,
    delete_variable,
    list_plans,
    list_product_audit,
    list_variables,
    upsert_plan,
    upsert_variable,
)
from app.schemas import AdminActionRequest, AppVariable, AuditLogEntry, PlanConfig, PlanUpsertRequest, VariableUpsertRequest

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/plans", response_model=list[PlanConfig])
async def get_plans() -> list[PlanConfig]:
    return list_plans()


@router.put("/plans/{plan_id}", response_model=PlanConfig)
async def put_plan(
    plan_id: str,
    payload: PlanUpsertRequest,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> PlanConfig:
    return upsert_plan(plan_id, payload, AdminActionRequest(actor=actor, reason=reason))


@router.delete("/plans/{plan_id}")
async def remove_plan(
    plan_id: str,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> dict[str, bool]:
    deleted = delete_plan(plan_id, AdminActionRequest(actor=actor, reason=reason))
    if not deleted:
        raise HTTPException(status_code=404, detail="plan_not_found")
    return {"deleted": True}


@router.get("/variables", response_model=list[AppVariable])
async def get_variables() -> list[AppVariable]:
    return list_variables()


@router.put("/variables/{key}", response_model=AppVariable)
async def put_variable(
    key: str,
    payload: VariableUpsertRequest,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> AppVariable:
    return upsert_variable(key, payload, AdminActionRequest(actor=actor, reason=reason))


@router.delete("/variables/{key}")
async def remove_variable(
    key: str,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> dict[str, bool]:
    deleted = delete_variable(key, AdminActionRequest(actor=actor, reason=reason))
    if not deleted:
        raise HTTPException(status_code=404, detail="variable_not_found")
    return {"deleted": True}


@router.get("/product-audit", response_model=list[AuditLogEntry])
async def get_product_audit(limit: int = Query(default=100, ge=1, le=1000)) -> list[AuditLogEntry]:
    return list_product_audit(limit=limit)
