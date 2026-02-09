from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import assert_same_user, get_authenticated_user, require_admin_access
from app.product_store import list_plans
from app.schemas import (
    PlanConfig,
    SubscriptionEntitlementResponse,
    SubscriptionEntitlementUpsertRequest,
    WebCheckoutSessionRequest,
    WebCheckoutSessionResponse,
)
from app.subscription_store import create_web_checkout_session, get_entitlement, list_entitlements, upsert_entitlement

router = APIRouter(prefix="/v1/subscriptions", tags=["subscriptions"])
admin_router = APIRouter(
    prefix="/v1/admin/subscriptions",
    tags=["admin", "subscriptions"],
    dependencies=[Depends(require_admin_access)],
)


@router.get("/entitlements/{user_id}", response_model=SubscriptionEntitlementResponse)
async def subscription_entitlement(
    user_id: str,
    auth_user_id: str = Depends(get_authenticated_user),
) -> SubscriptionEntitlementResponse:
    assert_same_user(auth_user_id, user_id)
    return get_entitlement(user_id)


@router.put("/entitlements/{user_id}", response_model=SubscriptionEntitlementResponse)
async def upsert_subscription_entitlement(
    user_id: str,
    payload: SubscriptionEntitlementUpsertRequest,
    auth_user_id: str = Depends(get_authenticated_user),
) -> SubscriptionEntitlementResponse:
    assert_same_user(auth_user_id, user_id)
    return upsert_entitlement(user_id, payload)


@router.get("/catalog", response_model=list[PlanConfig])
async def subscription_catalog() -> list[PlanConfig]:
    return [plan for plan in list_plans() if plan.is_active]


@router.post("/web/checkout-session", response_model=WebCheckoutSessionResponse)
async def web_checkout_session(
    payload: WebCheckoutSessionRequest,
    auth_user_id: str = Depends(get_authenticated_user),
) -> WebCheckoutSessionResponse:
    assert_same_user(auth_user_id, payload.user_id)
    try:
        return create_web_checkout_session(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.get("/entitlements", response_model=list[SubscriptionEntitlementResponse])
async def admin_list_subscription_entitlements(limit: int = 200) -> list[SubscriptionEntitlementResponse]:
    return list_entitlements(limit=limit)
