from __future__ import annotations

import os
from urllib.parse import quote_plus
from uuid import uuid4

from sqlalchemy import desc, select

from app.db import session_scope
from app.models import SubscriptionEntitlementModel, SubscriptionWebhookEventModel
from app.product_store import list_plans
from app.schemas import (
    GooglePlayWebhookRequest,
    WebBillingWebhookRequest,
    WebCheckoutSessionRequest,
    WebCheckoutSessionResponse,
    StoreKitWebhookRequest,
    SubscriptionEntitlementResponse,
    SubscriptionEntitlementUpsertRequest,
    SubscriptionSource,
    SubscriptionStatus,
    WebhookProcessResponse,
)
from app.time_utils import utc_now

_STATUS_PRIORITY: dict[str, int] = {
    SubscriptionStatus.active.value: 4,
    SubscriptionStatus.canceled.value: 3,
    SubscriptionStatus.expired.value: 2,
    SubscriptionStatus.inactive.value: 1,
}


def get_entitlement(user_id: str) -> SubscriptionEntitlementResponse:
    with session_scope() as session:
        model = session.get(SubscriptionEntitlementModel, user_id)
        if not model:
            return SubscriptionEntitlementResponse(
                user_id=user_id,
                plan_id="free",
                status=SubscriptionStatus.inactive,
                source=SubscriptionSource.manual,
                metadata={},
            )
        return _to_schema(model)


def list_entitlements(limit: int = 200) -> list[SubscriptionEntitlementResponse]:
    with session_scope() as session:
        stmt = select(SubscriptionEntitlementModel).order_by(desc(SubscriptionEntitlementModel.updated_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [_to_schema(row) for row in rows]


def upsert_entitlement(user_id: str, payload: SubscriptionEntitlementUpsertRequest) -> SubscriptionEntitlementResponse:
    with session_scope() as session:
        model = session.get(SubscriptionEntitlementModel, user_id)
        if not model:
            model = SubscriptionEntitlementModel(user_id=user_id)
            session.add(model)

        model.plan_id = payload.plan_id
        model.status = payload.status.value
        model.source = payload.source.value
        model.product_id = payload.product_id
        model.original_transaction_id = payload.original_transaction_id
        model.renews_at = payload.renews_at
        model.expires_at = payload.expires_at
        model.metadata_json = payload.metadata
        model.updated_at = utc_now()

        return _to_schema(model)


def handle_storekit_webhook(payload: StoreKitWebhookRequest, header_secret: str | None) -> WebhookProcessResponse:
    expected_secret = os.getenv("STOREKIT_WEBHOOK_SECRET")
    if expected_secret and header_secret != expected_secret:
        return WebhookProcessResponse(event_id=payload.event_id or "unknown", processed=False, message="unauthorized")

    event_id = payload.event_id or f"storekit_{uuid4()}"

    with session_scope() as session:
        existing = _get_webhook_event(session, event_id)
        if existing:
            return WebhookProcessResponse(event_id=event_id, processed=False, message="duplicate_event")

        event_model = SubscriptionWebhookEventModel(
            provider="storekit",
            event_id=event_id,
            payload_json=payload.model_dump(mode="json"),
            processed=False,
        )
        session.add(event_model)

        plan_id = _resolve_plan_id_for_product("ios", payload.product_id)
        _apply_webhook_entitlement_update(
            session=session,
            user_id=payload.user_id,
            plan_id=plan_id,
            status=payload.status.value,
            source=SubscriptionSource.ios.value,
            product_id=payload.product_id,
            original_transaction_id=payload.original_transaction_id,
            renews_at=payload.renews_at,
            expires_at=payload.expires_at,
            metadata=payload.metadata,
        )

        event_model.processed = True
        event_model.processing_error = None
        event_model.processed_at = utc_now()

    return WebhookProcessResponse(event_id=event_id, processed=True, message="processed")


def handle_google_play_webhook(payload: GooglePlayWebhookRequest, header_secret: str | None) -> WebhookProcessResponse:
    expected_secret = os.getenv("GOOGLE_PLAY_WEBHOOK_SECRET")
    if expected_secret and header_secret != expected_secret:
        return WebhookProcessResponse(event_id=payload.event_id or "unknown", processed=False, message="unauthorized")

    event_id = payload.event_id or f"gplay_{uuid4()}"

    with session_scope() as session:
        existing = _get_webhook_event(session, event_id)
        if existing:
            return WebhookProcessResponse(event_id=event_id, processed=False, message="duplicate_event")

        event_model = SubscriptionWebhookEventModel(
            provider="google_play",
            event_id=event_id,
            payload_json=payload.model_dump(mode="json"),
            processed=False,
        )
        session.add(event_model)

        plan_id = _resolve_plan_id_for_product("android", payload.product_id)
        _apply_webhook_entitlement_update(
            session=session,
            user_id=payload.user_id,
            plan_id=plan_id,
            status=payload.status.value,
            source=SubscriptionSource.android.value,
            product_id=payload.product_id,
            original_transaction_id=payload.original_transaction_id,
            renews_at=payload.renews_at,
            expires_at=payload.expires_at,
            metadata=payload.metadata,
        )

        event_model.processed = True
        event_model.processing_error = None
        event_model.processed_at = utc_now()

    return WebhookProcessResponse(event_id=event_id, processed=True, message="processed")


def handle_web_billing_webhook(payload: WebBillingWebhookRequest, header_secret: str | None) -> WebhookProcessResponse:
    expected_secret = os.getenv("WEB_BILLING_WEBHOOK_SECRET")
    if expected_secret and header_secret != expected_secret:
        return WebhookProcessResponse(event_id=payload.event_id or "unknown", processed=False, message="unauthorized")

    event_id = payload.event_id or f"web_{uuid4()}"

    with session_scope() as session:
        existing = _get_webhook_event(session, event_id)
        if existing:
            return WebhookProcessResponse(event_id=event_id, processed=False, message="duplicate_event")

        event_model = SubscriptionWebhookEventModel(
            provider="web_billing",
            event_id=event_id,
            payload_json=payload.model_dump(mode="json"),
            processed=False,
        )
        session.add(event_model)

        plan_id = _resolve_plan_id_for_product("web", payload.product_id)
        _apply_webhook_entitlement_update(
            session=session,
            user_id=payload.user_id,
            plan_id=plan_id,
            status=payload.status.value,
            source=SubscriptionSource.web.value,
            product_id=payload.product_id,
            original_transaction_id=payload.original_transaction_id,
            renews_at=payload.renews_at,
            expires_at=payload.expires_at,
            metadata=payload.metadata,
        )

        event_model.processed = True
        event_model.processing_error = None
        event_model.processed_at = utc_now()

    return WebhookProcessResponse(event_id=event_id, processed=True, message="processed")


def create_web_checkout_session(payload: WebCheckoutSessionRequest) -> WebCheckoutSessionResponse:
    plan = next((item for item in list_plans() if item.plan_id == payload.plan_id and item.is_active), None)
    if not plan:
        raise ValueError("plan_not_found_or_inactive")

    if not plan.web_product_id:
        raise ValueError("plan_missing_web_product_id")

    session_id = f"wcs_{uuid4().hex}"
    checkout_base = os.getenv("WEB_BILLING_CHECKOUT_BASE_URL", "https://payments.example.com/checkout")
    checkout_url = (
        f"{checkout_base}"
        f"?session_id={session_id}"
        f"&user_id={quote_plus(payload.user_id)}"
        f"&plan_id={quote_plus(plan.plan_id)}"
        f"&product_id={quote_plus(plan.web_product_id)}"
        f"&success_url={quote_plus(payload.success_url)}"
        f"&cancel_url={quote_plus(payload.cancel_url)}"
    )

    return WebCheckoutSessionResponse(
        session_id=session_id,
        checkout_url=checkout_url,
        provider="stripe",
    )


def _resolve_plan_id_for_product(source: str, product_id: str) -> str:
    for plan in list_plans():
        if source == "ios" and plan.ios_product_id and plan.ios_product_id == product_id:
            return plan.plan_id
        if source == "android" and plan.android_product_id and plan.android_product_id == product_id:
            return plan.plan_id
        if source == "web" and plan.web_product_id and plan.web_product_id == product_id:
            return plan.plan_id
    return "pro"


def _apply_webhook_entitlement_update(
    *,
    session,
    user_id: str,
    plan_id: str,
    status: str,
    source: str,
    product_id: str,
    original_transaction_id: str | None,
    renews_at,
    expires_at,
    metadata: dict,
) -> None:
    entitlement = session.get(SubscriptionEntitlementModel, user_id)
    if not entitlement:
        entitlement = SubscriptionEntitlementModel(user_id=user_id)
        session.add(entitlement)

    if not _should_apply_candidate(
        current_plan_id=entitlement.plan_id,
        current_status=entitlement.status,
        current_renews_at=entitlement.renews_at,
        current_expires_at=entitlement.expires_at,
        candidate_plan_id=plan_id,
        candidate_status=status,
        candidate_renews_at=renews_at,
        candidate_expires_at=expires_at,
    ):
        return

    entitlement.plan_id = plan_id
    entitlement.status = status
    entitlement.source = source
    entitlement.product_id = product_id
    entitlement.original_transaction_id = original_transaction_id
    entitlement.renews_at = renews_at
    entitlement.expires_at = expires_at
    entitlement.metadata_json = metadata
    entitlement.updated_at = utc_now()


def _should_apply_candidate(
    *,
    current_plan_id: str,
    current_status: str,
    current_renews_at,
    current_expires_at,
    candidate_plan_id: str,
    candidate_status: str,
    candidate_renews_at,
    candidate_expires_at,
) -> bool:
    if current_status == SubscriptionStatus.active.value and candidate_status != SubscriptionStatus.active.value:
        return False
    if candidate_status == SubscriptionStatus.active.value and current_status != SubscriptionStatus.active.value:
        return True

    if current_status == SubscriptionStatus.active.value and candidate_status == SubscriptionStatus.active.value:
        current_rank = _plan_price_rank(current_plan_id)
        candidate_rank = _plan_price_rank(candidate_plan_id)
        if candidate_rank != current_rank:
            return candidate_rank > current_rank

        if _entitlement_end_key(candidate_renews_at, candidate_expires_at) != _entitlement_end_key(
            current_renews_at,
            current_expires_at,
        ):
            return _entitlement_end_key(candidate_renews_at, candidate_expires_at) > _entitlement_end_key(
                current_renews_at,
                current_expires_at,
            )
        return True

    current_status_rank = _STATUS_PRIORITY.get(current_status, 0)
    candidate_status_rank = _STATUS_PRIORITY.get(candidate_status, 0)
    if candidate_status_rank != current_status_rank:
        return candidate_status_rank > current_status_rank

    if _entitlement_end_key(candidate_renews_at, candidate_expires_at) != _entitlement_end_key(
        current_renews_at,
        current_expires_at,
    ):
        return _entitlement_end_key(candidate_renews_at, candidate_expires_at) > _entitlement_end_key(
            current_renews_at,
            current_expires_at,
        )
    return True


def _entitlement_end_key(renews_at, expires_at) -> tuple[int, object]:
    if renews_at is not None:
        return (2, renews_at)
    if expires_at is not None:
        return (1, expires_at)
    return (0, 0)


def _plan_price_rank(plan_id: str) -> float:
    for plan in list_plans():
        if plan.plan_id == plan_id:
            return float(plan.monthly_price_usd)
    if plan_id == "free":
        return 0.0
    return 1.0


def _get_webhook_event(session, event_id: str) -> SubscriptionWebhookEventModel | None:
    stmt = select(SubscriptionWebhookEventModel).where(SubscriptionWebhookEventModel.event_id == event_id)
    return session.execute(stmt).scalar_one_or_none()


def _to_schema(model: SubscriptionEntitlementModel) -> SubscriptionEntitlementResponse:
    return SubscriptionEntitlementResponse(
        user_id=model.user_id,
        plan_id=model.plan_id,
        status=SubscriptionStatus(model.status),
        source=SubscriptionSource(model.source),
        product_id=model.product_id,
        original_transaction_id=model.original_transaction_id,
        renews_at=model.renews_at,
        expires_at=model.expires_at,
        metadata=model.metadata_json or {},
    )
