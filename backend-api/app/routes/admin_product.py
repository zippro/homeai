from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_admin_access
from app.product_store import (
    delete_style,
    delete_plan,
    delete_variable,
    list_plans,
    list_product_audit,
    list_styles,
    seed_default_styles,
    list_variables,
    upsert_style,
    upsert_plan,
    upsert_variable,
)
from app.schemas import (
    AdminActionRequest,
    AppVariable,
    AuditLogEntry,
    PlanConfig,
    PlanUpsertRequest,
    StylePreset,
    StyleSeedResponse,
    StyleUpsertRequest,
    VariableUpsertRequest,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin_access)])


@router.get("/plans", response_model=list[PlanConfig])
async def get_plans() -> list[PlanConfig]:
    return list_plans()


@router.get("/styles", response_model=list[StylePreset])
async def get_styles(active_only: bool = Query(default=False)) -> list[StylePreset]:
    return list_styles(active_only=active_only)


@router.put("/styles/{style_id}", response_model=StylePreset)
async def put_style(
    style_id: str,
    payload: StyleUpsertRequest,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> StylePreset:
    return upsert_style(style_id, payload, AdminActionRequest(actor=actor, reason=reason))


@router.post("/styles/seed-defaults", response_model=StyleSeedResponse)
async def post_seed_default_styles(
    overwrite: bool = Query(default=False),
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> StyleSeedResponse:
    return seed_default_styles(
        action=AdminActionRequest(actor=actor, reason=reason),
        overwrite=overwrite,
    )


@router.delete("/styles/{style_id}")
async def remove_style(
    style_id: str,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> dict[str, bool]:
    deleted = delete_style(style_id, AdminActionRequest(actor=actor, reason=reason))
    if not deleted:
        raise HTTPException(status_code=404, detail="style_not_found")
    return {"deleted": True}


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
