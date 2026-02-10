from __future__ import annotations

import os
import unittest
from unittest.mock import patch

try:
    from sqlalchemy import delete

    from app.bootstrap import init_database
    from app.db import session_scope
    from app.models import SubscriptionEntitlementModel, SubscriptionWebhookEventModel
    from app.schemas import (
        GooglePlayWebhookRequest,
        StoreKitWebhookRequest,
        SubscriptionEntitlementUpsertRequest,
        SubscriptionSource,
        SubscriptionStatus,
        WebBillingWebhookRequest,
        WebCheckoutSessionRequest,
    )
    from app.subscription_store import (
        create_web_checkout_session,
        get_entitlement,
        handle_google_play_webhook,
        handle_storekit_webhook,
        handle_web_billing_webhook,
        upsert_entitlement,
    )

    _SUBSCRIPTION_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _SUBSCRIPTION_TESTS_AVAILABLE = False


@unittest.skipUnless(_SUBSCRIPTION_TESTS_AVAILABLE, "sqlalchemy dependency is not installed in this environment")
class SubscriptionStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()

    def setUp(self) -> None:
        with session_scope() as session:
            session.execute(delete(SubscriptionEntitlementModel))
            session.execute(delete(SubscriptionWebhookEventModel))
        os.environ.pop("WEB_BILLING_WEBHOOK_SECRET", None)
        os.environ.pop("STOREKIT_WEBHOOK_SECRET", None)
        os.environ.pop("GOOGLE_PLAY_WEBHOOK_SECRET", None)
        os.environ.pop("APP_ENV", None)

    def test_create_web_checkout_session_returns_checkout_url(self) -> None:
        session_data = create_web_checkout_session(
            WebCheckoutSessionRequest(
                user_id="web-user-1",
                plan_id="pro",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )
        )
        self.assertTrue(session_data.session_id.startswith("wcs_"))
        self.assertIn("plan_id=pro", session_data.checkout_url)
        self.assertIn("product_id=pro_monthly_web", session_data.checkout_url)
        self.assertIn("user_id=web-user-1", session_data.checkout_url)
        self.assertEqual(session_data.provider, "stripe")

    def test_web_billing_webhook_updates_entitlement_and_prevents_duplicate(self) -> None:
        payload = WebBillingWebhookRequest(
            event_id="web_evt_1",
            user_id="web-user-2",
            product_id="pro_monthly_web",
            status=SubscriptionStatus.active,
            metadata={"origin": "web-checkout"},
        )

        first = handle_web_billing_webhook(payload, header_secret=None)
        second = handle_web_billing_webhook(payload, header_secret=None)
        entitlement = get_entitlement("web-user-2")

        self.assertTrue(first.processed)
        self.assertFalse(second.processed)
        self.assertEqual(second.message, "duplicate_event")
        self.assertEqual(entitlement.plan_id, "pro")
        self.assertEqual(entitlement.source.value, "web")
        self.assertEqual(entitlement.status.value, "active")
        self.assertEqual(entitlement.product_id, "pro_monthly_web")
        self.assertEqual(entitlement.metadata.get("origin"), "web-checkout")

    def test_web_billing_webhook_honors_secret_when_configured(self) -> None:
        os.environ["WEB_BILLING_WEBHOOK_SECRET"] = "secret123"
        payload = WebBillingWebhookRequest(
            event_id="web_evt_2",
            user_id="web-user-3",
            product_id="pro_monthly_web",
            status=SubscriptionStatus.active,
        )

        unauthorized = handle_web_billing_webhook(payload, header_secret="wrong")
        entitlement_after_unauth = get_entitlement("web-user-3")
        authorized = handle_web_billing_webhook(payload, header_secret="secret123")
        entitlement_after_auth = get_entitlement("web-user-3")

        self.assertFalse(unauthorized.processed)
        self.assertEqual(unauthorized.message, "unauthorized")
        self.assertEqual(entitlement_after_unauth.plan_id, "free")
        self.assertEqual(entitlement_after_unauth.status.value, "inactive")

        self.assertTrue(authorized.processed)
        self.assertEqual(authorized.message, "processed")
        self.assertEqual(entitlement_after_auth.plan_id, "pro")
        self.assertEqual(entitlement_after_auth.source.value, "web")

    def test_web_billing_webhook_requires_secret_in_production_when_not_configured(self) -> None:
        payload = WebBillingWebhookRequest(
            event_id="web_evt_prod_reject_1",
            user_id="web-user-prod-1",
            product_id="pro_monthly_web",
            status=SubscriptionStatus.active,
        )
        with patch.dict(os.environ, {"APP_ENV": "production", "WEB_BILLING_WEBHOOK_SECRET": ""}, clear=False):
            unauthorized = handle_web_billing_webhook(payload, header_secret=None)
        entitlement = get_entitlement("web-user-prod-1")

        self.assertFalse(unauthorized.processed)
        self.assertEqual(unauthorized.message, "unauthorized")
        self.assertEqual(entitlement.plan_id, "free")
        self.assertEqual(entitlement.status.value, "inactive")

    def test_active_entitlement_is_not_downgraded_by_non_active_webhook(self) -> None:
        active_payload = WebBillingWebhookRequest(
            event_id="web_evt_keep_active_1",
            user_id="web-user-4",
            product_id="pro_monthly_web",
            status=SubscriptionStatus.active,
            metadata={"stage": "active"},
        )
        downgrade_payload = GooglePlayWebhookRequest(
            event_id="gplay_evt_keep_active_1",
            user_id="web-user-4",
            product_id="pro_monthly_android",
            status=SubscriptionStatus.expired,
            metadata={"stage": "expired"},
        )

        first = handle_web_billing_webhook(active_payload, header_secret=None)
        second = handle_google_play_webhook(downgrade_payload, header_secret=None)
        entitlement = get_entitlement("web-user-4")

        self.assertTrue(first.processed)
        self.assertTrue(second.processed)
        self.assertEqual(entitlement.status.value, "active")
        self.assertEqual(entitlement.source.value, "web")
        self.assertEqual(entitlement.metadata.get("stage"), "active")

    def test_active_candidate_upgrades_manual_free_entitlement(self) -> None:
        upsert_entitlement(
            "web-user-5",
            SubscriptionEntitlementUpsertRequest(
                plan_id="free",
                status=SubscriptionStatus.active,
                source=SubscriptionSource.manual,
                product_id="free_manual",
            ),
        )

        upgrade_payload = StoreKitWebhookRequest(
            event_id="storekit_evt_upgrade_1",
            user_id="web-user-5",
            product_id="pro_monthly_ios",
            status=SubscriptionStatus.active,
            metadata={"origin": "ios_purchase"},
        )

        result = handle_storekit_webhook(upgrade_payload, header_secret=None)
        entitlement = get_entitlement("web-user-5")

        self.assertTrue(result.processed)
        self.assertEqual(entitlement.plan_id, "pro")
        self.assertEqual(entitlement.status.value, "active")
        self.assertEqual(entitlement.source.value, "ios")
        self.assertEqual(entitlement.metadata.get("origin"), "ios_purchase")


if __name__ == "__main__":
    unittest.main()
