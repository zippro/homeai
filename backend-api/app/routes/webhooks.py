from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.schemas import (
    GooglePlayWebhookRequest,
    StoreKitWebhookRequest,
    WebBillingWebhookRequest,
    WebhookProcessResponse,
)
from app.subscription_store import handle_google_play_webhook, handle_storekit_webhook, handle_web_billing_webhook

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks", "subscriptions"])


@router.post("/storekit", response_model=WebhookProcessResponse)
async def storekit_webhook(
    payload: StoreKitWebhookRequest,
    x_webhook_secret: str | None = Header(default=None),
) -> WebhookProcessResponse:
    result = handle_storekit_webhook(payload, x_webhook_secret)
    if not result.processed and result.message == "unauthorized":
        raise HTTPException(status_code=401, detail="unauthorized")
    return result


@router.post("/google-play", response_model=WebhookProcessResponse)
async def google_play_webhook(
    payload: GooglePlayWebhookRequest,
    x_webhook_secret: str | None = Header(default=None),
) -> WebhookProcessResponse:
    result = handle_google_play_webhook(payload, x_webhook_secret)
    if not result.processed and result.message == "unauthorized":
        raise HTTPException(status_code=401, detail="unauthorized")
    return result


@router.post("/web-billing", response_model=WebhookProcessResponse)
async def web_billing_webhook(
    payload: WebBillingWebhookRequest,
    x_webhook_secret: str | None = Header(default=None),
) -> WebhookProcessResponse:
    result = handle_web_billing_webhook(payload, x_webhook_secret)
    if not result.processed and result.message == "unauthorized":
        raise HTTPException(status_code=401, detail="unauthorized")
    return result
