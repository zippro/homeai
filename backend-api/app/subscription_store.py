from __future__ import annotations

import os
from datetime import datetime
from uuid import uuid4

from sqlalchemy import desc, select

from app.db import session_scope
from app.models import SubscriptionEntitlementModel, SubscriptionWebhookEventModel
from app.product_store import list_plans
from app.schemas import (
    GooglePlayWebhookRequest,
    StoreKitWebhookRequest,
    SubscriptionEntitlementResponse,
    SubscriptionEntitlementUpsertRequest,
    SubscriptionSource,
    SubscriptionStatus,
    WebhookProcessResponse,
)


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
        model.updated_at = datetime.utcnow()

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
        entitlement = session.get(SubscriptionEntitlementModel, payload.user_id)
        if not entitlement:
            entitlement = SubscriptionEntitlementModel(user_id=payload.user_id)
            session.add(entitlement)

        entitlement.plan_id = plan_id
        entitlement.status = payload.status.value
        entitlement.source = SubscriptionSource.ios.value
        entitlement.product_id = payload.product_id
        entitlement.original_transaction_id = payload.original_transaction_id
        entitlement.renews_at = payload.renews_at
        entitlement.expires_at = payload.expires_at
        entitlement.metadata_json = payload.metadata
        entitlement.updated_at = datetime.utcnow()

        event_model.processed = True
        event_model.processing_error = None
        event_model.processed_at = datetime.utcnow()

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
        entitlement = session.get(SubscriptionEntitlementModel, payload.user_id)
        if not entitlement:
            entitlement = SubscriptionEntitlementModel(user_id=payload.user_id)
            session.add(entitlement)

        entitlement.plan_id = plan_id
        entitlement.status = payload.status.value
        entitlement.source = SubscriptionSource.android.value
        entitlement.product_id = payload.product_id
        entitlement.original_transaction_id = payload.original_transaction_id
        entitlement.renews_at = payload.renews_at
        entitlement.expires_at = payload.expires_at
        entitlement.metadata_json = payload.metadata
        entitlement.updated_at = datetime.utcnow()

        event_model.processed = True
        event_model.processing_error = None
        event_model.processed_at = datetime.utcnow()

    return WebhookProcessResponse(event_id=event_id, processed=True, message="processed")


def _resolve_plan_id_for_product(source: str, product_id: str) -> str:
    for plan in list_plans():
        if source == "ios" and plan.ios_product_id and plan.ios_product_id == product_id:
            return plan.plan_id
        if source == "android" and plan.android_product_id and plan.android_product_id == product_id:
            return plan.plan_id
    return "pro"


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
