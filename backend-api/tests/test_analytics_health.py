from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from app.time_utils import utc_now

try:
    from sqlalchemy import delete

    from app.analytics_store import get_analytics_dashboard, get_analytics_overview, ingest_event
    from app.bootstrap import init_database
    from app.db import session_scope
    from app.models import (
        AnalyticsEventModel,
        AuthSessionModel,
        CreditLedgerEntryModel,
        ExperimentAssignmentModel,
        ExperimentModel,
        RenderJobModel,
        SubscriptionEntitlementModel,
    )
    from app.provider_health_store import get_provider_health
    from app.schemas import AnalyticsEventRequest, JobStatus, OperationType

    _ANALYTICS_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _ANALYTICS_TESTS_AVAILABLE = False


@unittest.skipUnless(_ANALYTICS_TESTS_AVAILABLE, "sqlalchemy dependency is not installed in this environment")
class AnalyticsAndHealthStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()

    def setUp(self) -> None:
        with session_scope() as session:
            session.execute(delete(ExperimentAssignmentModel))
            session.execute(delete(ExperimentModel))
            session.execute(delete(SubscriptionEntitlementModel))
            session.execute(delete(CreditLedgerEntryModel))
            session.execute(delete(RenderJobModel))
            session.execute(delete(AuthSessionModel))
            session.execute(delete(AnalyticsEventModel))

    def test_analytics_overview_aggregates_render_metrics(self) -> None:
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_dispatched",
                provider="fal",
                operation=OperationType.restyle,
                status=JobStatus.completed,
                latency_ms=900,
                cost_usd=0.02,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                provider="openai",
                operation=OperationType.restyle,
                status=JobStatus.failed,
                latency_ms=3000,
                cost_usd=0.03,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                provider="fal",
                operation=OperationType.restyle,
                status=JobStatus.completed,
                latency_ms=1100,
                cost_usd=0.04,
            )
        )

        overview = get_analytics_overview()
        self.assertEqual(overview.total_events, 3)
        self.assertEqual(overview.render_events, 3)
        self.assertEqual(overview.render_success, 2)
        self.assertEqual(overview.render_failed, 1)
        self.assertAlmostEqual(overview.render_success_rate, 66.67, places=2)
        self.assertAlmostEqual(overview.avg_latency_ms or 0.0, 1666.67, places=2)
        self.assertAlmostEqual(overview.p95_latency_ms or 0.0, 3000.0, places=2)
        self.assertAlmostEqual(overview.total_cost_usd, 0.09, places=6)
        self.assertEqual(overview.provider_event_counts, {"fal": 2, "openai": 1})
        self.assertEqual(overview.provider_success_rate, {"fal": 100.0, "openai": 0.0})

    def test_provider_health_summary_shape(self) -> None:
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_dispatched",
                provider="fal",
                operation=OperationType.repaint,
                status=JobStatus.completed,
                latency_ms=1000,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                provider="fal",
                operation=OperationType.repaint,
                status=JobStatus.failed,
                latency_ms=3000,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_dispatched",
                provider="openai",
                operation=OperationType.repaint,
                status=JobStatus.completed,
                latency_ms=2500,
            )
        )
        ingest_event(AnalyticsEventRequest(event_name="session_started", provider="fal"))

        health = get_provider_health(hours=24)

        self.assertEqual(health["fal"]["total_events"], 2)
        self.assertEqual(health["fal"]["failed_events"], 1)
        self.assertAlmostEqual(float(health["fal"]["success_rate"]), 50.0, places=2)
        self.assertAlmostEqual(float(health["fal"]["avg_latency_ms"]), 2000.0, places=2)
        self.assertAlmostEqual(float(health["fal"]["health_score"]), 65.0, places=2)

        self.assertEqual(health["openai"]["total_events"], 1)
        self.assertEqual(health["openai"]["failed_events"], 0)
        self.assertAlmostEqual(float(health["openai"]["success_rate"]), 100.0, places=2)
        self.assertAlmostEqual(float(health["openai"]["avg_latency_ms"]), 2500.0, places=2)
        self.assertAlmostEqual(float(health["openai"]["health_score"]), 100.0, places=2)

    def test_analytics_dashboard_includes_health_and_business_metrics(self) -> None:
        now = utc_now()
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_dispatched",
                user_id="u1",
                platform="ios",
                provider="fal",
                operation=OperationType.replace,
                status=JobStatus.completed,
                latency_ms=800,
                cost_usd=0.015,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                user_id="u2",
                platform="android",
                provider="openai",
                operation=OperationType.replace,
                status=JobStatus.failed,
                latency_ms=2400,
                cost_usd=0.025,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="checkout_started",
                user_id="u1",
                platform="web",
                occurred_at=now,
            )
        )

        with session_scope() as session:
            session.add(
                AuthSessionModel(
                    token="dev_token_u1",
                    user_id="u1",
                    platform="web",
                    created_at=now,
                    expires_at=now + timedelta(days=1),
                    revoked_at=None,
                )
            )
            session.add(
                CreditLedgerEntryModel(
                    user_id="u1",
                    delta=-1,
                    reason="render_preview",
                    idempotency_key="credit_preview_u1",
                    metadata_json={},
                    created_at=now,
                )
            )
            session.add(
                CreditLedgerEntryModel(
                    user_id="u1",
                    delta=-2,
                    reason="render_final",
                    idempotency_key="credit_final_u1",
                    metadata_json={},
                    created_at=now,
                )
            )
            session.add(
                SubscriptionEntitlementModel(
                    user_id="u1",
                    plan_id="pro",
                    status="active",
                    source="web",
                    product_id="pro_monthly_web",
                    original_transaction_id="tx_u1",
                    renews_at=now + timedelta(days=30),
                    expires_at=None,
                    metadata_json={},
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                ExperimentModel(
                    experiment_id="pricing_paywall_v1",
                    payload_json={
                        "name": "Pricing Paywall V1",
                        "is_active": True,
                        "assignment_unit": "user_id",
                        "primary_metric": "upgrade_conversion_7d",
                        "variants": [
                            {"variant_id": "control", "weight": 50, "config": {"paywall_mode": "on_exhaustion"}},
                            {"variant_id": "treatment", "weight": 50, "config": {"paywall_mode": "after_preview"}},
                        ],
                    },
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                ExperimentAssignmentModel(
                    experiment_id="pricing_paywall_v1",
                    user_id="u1",
                    variant_id="control",
                    assigned_at=now,
                )
            )
            session.add(
                ExperimentAssignmentModel(
                    experiment_id="pricing_paywall_v1",
                    user_id="u2",
                    variant_id="treatment",
                    assigned_at=now,
                )
            )

        dashboard = get_analytics_dashboard(hours=24)
        self.assertEqual(dashboard.summary.window_hours, 24)
        self.assertEqual(dashboard.summary.total_events, 3)
        self.assertEqual(dashboard.summary.render_events, 2)
        self.assertEqual(dashboard.summary.unique_users, 2)
        self.assertEqual(dashboard.summary.active_render_users, 2)
        self.assertAlmostEqual(dashboard.summary.render_success_rate, 50.0, places=2)
        self.assertAlmostEqual(dashboard.summary.total_cost_usd, 0.04, places=6)

        providers = {item.provider: item for item in dashboard.provider_breakdown}
        self.assertIn("fal", providers)
        self.assertIn("openai", providers)
        self.assertEqual(providers["fal"].total_events, 1)
        self.assertEqual(providers["openai"].total_events, 1)

        platforms = {item.platform: item for item in dashboard.platform_breakdown}
        self.assertIn("ios", platforms)
        self.assertIn("android", platforms)

        self.assertEqual(dashboard.funnel.login_users, 1)
        self.assertEqual(dashboard.funnel.preview_users, 1)
        self.assertEqual(dashboard.funnel.final_users, 1)
        self.assertEqual(dashboard.funnel.checkout_starts, 1)
        self.assertEqual(dashboard.funnel.paid_activations, 1)
        self.assertAlmostEqual(dashboard.funnel.checkout_to_paid_rate, 100.0, places=2)

        source_rows = {item.source: item for item in dashboard.subscription_sources}
        self.assertIn("web", source_rows)
        self.assertEqual(source_rows["web"].active_subscriptions, 1)
        self.assertAlmostEqual(source_rows["web"].active_share_pct, 100.0, places=2)

        self.assertEqual(len(dashboard.experiment_breakdown), 1)
        experiment = dashboard.experiment_breakdown[0]
        self.assertEqual(experiment.experiment_id, "pricing_paywall_v1")
        self.assertEqual(experiment.total_assigned_users, 2)
        self.assertEqual(experiment.active_paid_users, 1)
        self.assertAlmostEqual(experiment.paid_conversion_rate, 50.0, places=2)


if __name__ == "__main__":
    unittest.main()
