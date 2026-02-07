from __future__ import annotations

from fastapi import APIRouter

from app.schemas import SubscriptionEntitlementResponse, SubscriptionEntitlementUpsertRequest
from app.subscription_store import get_entitlement, list_entitlements, upsert_entitlement

router = APIRouter(prefix="/v1/subscriptions", tags=["subscriptions"])
admin_router = APIRouter(prefix="/v1/admin/subscriptions", tags=["admin", "subscriptions"])


@router.get("/entitlements/{user_id}", response_model=SubscriptionEntitlementResponse)
async def subscription_entitlement(user_id: str) -> SubscriptionEntitlementResponse:
    return get_entitlement(user_id)


@router.put("/entitlements/{user_id}", response_model=SubscriptionEntitlementResponse)
async def upsert_subscription_entitlement(
    user_id: str,
    payload: SubscriptionEntitlementUpsertRequest,
) -> SubscriptionEntitlementResponse:
    return upsert_entitlement(user_id, payload)


@admin_router.get("/entitlements", response_model=list[SubscriptionEntitlementResponse])
async def admin_list_subscription_entitlements(limit: int = 200) -> list[SubscriptionEntitlementResponse]:
    return list_entitlements(limit=limit)
