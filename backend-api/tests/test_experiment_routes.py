from __future__ import annotations

import unittest
from datetime import timedelta
from app.time_utils import utc_now

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import delete

    from app.analytics_store import ingest_event
    from app.bootstrap import init_database
    from app.db import session_scope
    from app.main import app
    from app.models import (
        AdminAuditLogModel,
        AnalyticsEventModel,
        CreditLedgerEntryModel,
        ExperimentAssignmentModel,
        ExperimentModel,
        SubscriptionEntitlementModel,
    )
    from app.schemas import AnalyticsEventRequest, JobStatus, OperationType

    _EXPERIMENT_ROUTE_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _EXPERIMENT_ROUTE_TESTS_AVAILABLE = False


@unittest.skipUnless(_EXPERIMENT_ROUTE_TESTS_AVAILABLE, "fastapi/sqlalchemy dependency is not installed")
class ExperimentRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        cls.client = TestClient(app)

    def setUp(self) -> None:
        with session_scope() as session:
            session.execute(delete(AnalyticsEventModel))
            session.execute(delete(CreditLedgerEntryModel))
            session.execute(delete(ExperimentAssignmentModel))
            session.execute(delete(ExperimentModel))
            session.execute(delete(SubscriptionEntitlementModel))
            session.execute(delete(AdminAuditLogModel).where(AdminAuditLogModel.domain == "experiments"))

    def test_guardrail_evaluate_endpoint_returns_summary(self) -> None:
        upsert_payload = {
            "name": "Guardrail API Test",
            "description": "api guardrail test",
            "is_active": True,
            "assignment_unit": "user_id",
            "primary_metric": "render_success_rate",
            "guardrails": {
                "render_events_min": 10,
                "render_success_rate_min": 80,
            },
            "variants": [
                {
                    "variant_id": "control",
                    "weight": 100,
                    "config": {},
                }
            ],
        }

        upsert_response = self.client.put(
            "/v1/admin/experiments/guardrail_api_test",
            params={"actor": "tests", "reason": "setup"},
            json=upsert_payload,
        )
        self.assertEqual(upsert_response.status_code, 200)

        for index in range(12):
            ingest_event(
                AnalyticsEventRequest(
                    event_name="render_status_updated",
                    user_id=f"route_guardrail_{index}",
                    provider="fal",
                    operation=OperationType.restyle,
                    status=JobStatus.failed,
                )
            )

        eval_response = self.client.post(
            "/v1/admin/experiments/guardrails/evaluate",
            params={"hours": 24, "dry_run": True, "actor": "tests", "reason": "check"},
        )
        self.assertEqual(eval_response.status_code, 200)
        payload = eval_response.json()

        self.assertIn("evaluated_count", payload)
        self.assertIn("breached_count", payload)
        self.assertIn("paused_count", payload)
        self.assertIn("evaluations", payload)

        self.assertGreaterEqual(payload["evaluated_count"], 1)
        self.assertGreaterEqual(payload["breached_count"], 1)
        self.assertEqual(payload["paused_count"], 0)

    def test_templates_endpoint_returns_default_templates(self) -> None:
        response = self.client.get("/v1/admin/experiments/templates")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertGreaterEqual(len(payload), 4)
        template_ids = {item["template_id"] for item in payload}
        self.assertIn("pricing_paywall_timing", template_ids)
        self.assertIn("provider_fallback_order", template_ids)

    def test_experiment_performance_endpoint_returns_recommendation(self) -> None:
        now = utc_now()
        upsert_payload = {
            "name": "Pricing API Perf",
            "description": "performance endpoint",
            "is_active": True,
            "assignment_unit": "user_id",
            "primary_metric": "upgrade_conversion_7d",
            "variants": [
                {"variant_id": "control", "weight": 50, "config": {}},
                {"variant_id": "treatment", "weight": 50, "config": {}},
            ],
        }

        upsert_response = self.client.put(
            "/v1/admin/experiments/pricing_api_perf",
            params={"actor": "tests", "reason": "setup"},
            json=upsert_payload,
        )
        self.assertEqual(upsert_response.status_code, 200)

        with session_scope() as session:
            for index in range(120):
                user_id = f"route_control_{index}"
                session.add(
                    ExperimentAssignmentModel(
                        experiment_id="pricing_api_perf",
                        user_id=user_id,
                        variant_id="control",
                        assigned_at=now,
                    )
                )
                if index < 20:
                    session.add(
                        SubscriptionEntitlementModel(
                            user_id=user_id,
                            plan_id="pro",
                            status="active",
                            source="web",
                            product_id="pro_monthly_web",
                            original_transaction_id=f"route_control_tx_{index}",
                            renews_at=None,
                            expires_at=None,
                            metadata_json={},
                            created_at=now,
                            updated_at=now,
                        )
                    )

            for index in range(120):
                user_id = f"route_treatment_{index}"
                session.add(
                    ExperimentAssignmentModel(
                        experiment_id="pricing_api_perf",
                        user_id=user_id,
                        variant_id="treatment",
                        assigned_at=now,
                    )
                )
                if index < 48:
                    session.add(
                        SubscriptionEntitlementModel(
                            user_id=user_id,
                            plan_id="pro",
                            status="active",
                            source="ios",
                            product_id="pro_monthly_ios",
                            original_transaction_id=f"route_treatment_tx_{index}",
                            renews_at=None,
                            expires_at=None,
                            metadata_json={},
                            created_at=now,
                            updated_at=now,
                        )
                    )

        response = self.client.get(
            "/v1/admin/experiments/pricing_api_perf/performance",
            params={"hours": 24},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["experiment_id"], "pricing_api_perf")
        self.assertEqual(payload["control_variant_id"], "control")
        self.assertEqual(payload["recommended_variant_id"], "treatment")
        self.assertGreaterEqual(payload["total_assigned_users"], 240)
        self.assertEqual(len(payload["variants"]), 2)
        variants = {item["variant_id"]: item for item in payload["variants"]}
        self.assertEqual((variants["control"].get("paid_source_breakdown") or {}).get("web"), 20)
        self.assertEqual((variants["treatment"].get("paid_source_breakdown") or {}).get("ios"), 48)

    def test_experiment_rollout_endpoint_applies_first_step(self) -> None:
        now = utc_now()
        upsert_payload = {
            "name": "Pricing API Rollout",
            "description": "rollout endpoint",
            "is_active": True,
            "assignment_unit": "user_id",
            "primary_metric": "upgrade_conversion_7d",
            "variants": [
                {"variant_id": "control", "weight": 50, "config": {}},
                {"variant_id": "treatment", "weight": 50, "config": {}},
            ],
        }

        upsert_response = self.client.put(
            "/v1/admin/experiments/pricing_api_rollout",
            params={"actor": "tests", "reason": "setup"},
            json=upsert_payload,
        )
        self.assertEqual(upsert_response.status_code, 200)

        with session_scope() as session:
            for index in range(120):
                user_id = f"route_rollout_control_{index}"
                session.add(
                    ExperimentAssignmentModel(
                        experiment_id="pricing_api_rollout",
                        user_id=user_id,
                        variant_id="control",
                        assigned_at=now,
                    )
                )
                if index < 20:
                    session.add(
                        SubscriptionEntitlementModel(
                            user_id=user_id,
                            plan_id="pro",
                            status="active",
                            source="web",
                            product_id="pro_monthly_web",
                            original_transaction_id=f"route_rollout_control_tx_{index}",
                            renews_at=None,
                            expires_at=None,
                            metadata_json={},
                            created_at=now,
                            updated_at=now,
                        )
                    )

            for index in range(120):
                user_id = f"route_rollout_treatment_{index}"
                session.add(
                    ExperimentAssignmentModel(
                        experiment_id="pricing_api_rollout",
                        user_id=user_id,
                        variant_id="treatment",
                        assigned_at=now,
                    )
                )
                if index < 48:
                    session.add(
                        SubscriptionEntitlementModel(
                            user_id=user_id,
                            plan_id="pro",
                            status="active",
                            source="ios",
                            product_id="pro_monthly_ios",
                            original_transaction_id=f"route_rollout_treatment_tx_{index}",
                            renews_at=None,
                            expires_at=None,
                            metadata_json={},
                            created_at=now,
                            updated_at=now,
                        )
                    )

        dry_run_response = self.client.post(
            "/v1/admin/experiments/pricing_api_rollout/rollout/evaluate",
            params={"hours": 24, "dry_run": True, "actor": "tests", "reason": "dry"},
        )
        self.assertEqual(dry_run_response.status_code, 200)
        dry_payload = dry_run_response.json()
        self.assertEqual(dry_payload["winner_variant_id"], "treatment")
        self.assertIsNone(dry_payload["blocked_reason"])
        self.assertEqual(dry_payload["current_rollout_percent"], 0)
        self.assertEqual(dry_payload["next_rollout_percent"], 10)
        self.assertFalse(dry_payload["applied"])

        live_response = self.client.post(
            "/v1/admin/experiments/pricing_api_rollout/rollout/evaluate",
            params={"hours": 24, "dry_run": False, "actor": "tests", "reason": "live"},
        )
        self.assertEqual(live_response.status_code, 200)
        live_payload = live_response.json()
        self.assertTrue(live_payload["applied"])
        self.assertEqual(live_payload["next_rollout_percent"], 10)

        experiments_response = self.client.get("/v1/admin/experiments")
        self.assertEqual(experiments_response.status_code, 200)
        experiments = experiments_response.json()
        target = next(item for item in experiments if item["experiment_id"] == "pricing_api_rollout")
        rollout_state = target.get("rollout_state") or {}
        self.assertEqual(rollout_state.get("winner_variant_id"), "treatment")
        self.assertEqual(int(rollout_state.get("rollout_percent") or 0), 10)

    def test_experiment_trends_endpoint_returns_bucketed_data(self) -> None:
        now = utc_now()
        bucket0_time = now - timedelta(hours=5, minutes=30)
        bucket1_time = now - timedelta(hours=3, minutes=30)
        upsert_payload = {
            "name": "Pricing API Trend",
            "description": "trends endpoint",
            "is_active": True,
            "assignment_unit": "user_id",
            "primary_metric": "upgrade_conversion_7d",
            "variants": [
                {"variant_id": "control", "weight": 50, "config": {}},
                {"variant_id": "treatment", "weight": 50, "config": {}},
            ],
        }

        upsert_response = self.client.put(
            "/v1/admin/experiments/pricing_api_trend",
            params={"actor": "tests", "reason": "setup"},
            json=upsert_payload,
        )
        self.assertEqual(upsert_response.status_code, 200)

        with session_scope() as session:
            session.add(
                ExperimentAssignmentModel(
                    experiment_id="pricing_api_trend",
                    user_id="route_trend_control",
                    variant_id="control",
                    assigned_at=bucket0_time,
                )
            )
            session.add(
                ExperimentAssignmentModel(
                    experiment_id="pricing_api_trend",
                    user_id="route_trend_treatment",
                    variant_id="treatment",
                    assigned_at=bucket0_time,
                )
            )
            session.add(
                CreditLedgerEntryModel(
                    user_id="route_trend_control",
                    delta=-1,
                    reason="render_preview",
                    idempotency_key=None,
                    metadata_json={},
                    created_at=bucket0_time,
                )
            )
            session.add(
                CreditLedgerEntryModel(
                    user_id="route_trend_treatment",
                    delta=-1,
                    reason="render_preview",
                    idempotency_key=None,
                    metadata_json={},
                    created_at=bucket1_time,
                )
            )
            session.add(
                SubscriptionEntitlementModel(
                    user_id="route_trend_control",
                    plan_id="pro",
                    status="active",
                    source="web",
                    product_id="pro_monthly_web",
                    original_transaction_id="route_trend_tx",
                    renews_at=None,
                    expires_at=None,
                    metadata_json={},
                    created_at=bucket0_time,
                    updated_at=bucket0_time,
                )
            )

        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                user_id="route_trend_control",
                provider="fal",
                operation=OperationType.restyle,
                status=JobStatus.completed,
                latency_ms=900,
                cost_usd=0.02,
                occurred_at=bucket0_time,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                user_id="route_trend_treatment",
                provider="fal",
                operation=OperationType.restyle,
                status=JobStatus.failed,
                latency_ms=1300,
                cost_usd=0.01,
                occurred_at=bucket1_time,
            )
        )

        response = self.client.get(
            "/v1/admin/experiments/pricing_api_trend/trends",
            params={"hours": 6, "bucket_hours": 2},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["experiment_id"], "pricing_api_trend")
        self.assertEqual(payload["window_hours"], 6)
        self.assertEqual(payload["bucket_hours"], 2)
        self.assertEqual(len(payload["variants"]), 2)
        control = next(item for item in payload["variants"] if item["variant_id"] == "control")
        self.assertEqual(len(control["points"]), 3)
        self.assertGreaterEqual(
            sum(int(point.get("render_events") or 0) for point in control["points"]),
            1,
        )

    def test_bulk_rollout_endpoint_returns_summary(self) -> None:
        payload = {
            "name": "Bulk Route Rollout",
            "description": "bulk route endpoint",
            "is_active": True,
            "assignment_unit": "user_id",
            "primary_metric": "upgrade_conversion_7d",
            "variants": [
                {"variant_id": "control", "weight": 50, "config": {}},
                {"variant_id": "treatment", "weight": 50, "config": {}},
            ],
        }

        for experiment_id in ("bulk_route_rollout_a", "bulk_route_rollout_b"):
            response = self.client.put(
                f"/v1/admin/experiments/{experiment_id}",
                params={"actor": "tests", "reason": "setup"},
                json=payload,
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/v1/admin/experiments/rollout/evaluate-all",
            params={"hours": 24, "dry_run": True, "actor": "tests", "reason": "bulk"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["window_hours"], 24)
        self.assertTrue(body["dry_run"])
        self.assertEqual(body["evaluated_count"], 2)
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["applied_count"], 0)
        ids = {item["experiment_id"] for item in body["results"]}
        self.assertEqual(ids, {"bulk_route_rollout_a", "bulk_route_rollout_b"})

    def test_experiment_automation_endpoint_returns_combined_response(self) -> None:
        payload = {
            "name": "Automation Route Rollout",
            "description": "automation route endpoint",
            "is_active": True,
            "assignment_unit": "user_id",
            "primary_metric": "upgrade_conversion_7d",
            "variants": [
                {"variant_id": "control", "weight": 50, "config": {}},
                {"variant_id": "treatment", "weight": 50, "config": {}},
            ],
        }

        response = self.client.put(
            "/v1/admin/experiments/automation_route_rollout",
            params={"actor": "tests", "reason": "setup"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/v1/admin/experiments/automation/run",
            params={"hours": 24, "dry_run": True, "rollout_limit": 50, "actor": "tests", "reason": "automation"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["dry_run"])
        self.assertEqual(body["window_hours"], 24)
        self.assertEqual(body["rollout_limit"], 50)
        self.assertIn("guardrails", body)
        self.assertIn("rollouts", body)
        self.assertGreaterEqual(body["guardrails"]["evaluated_count"], 1)
        self.assertEqual(body["rollouts"]["evaluated_count"], 1)
        self.assertEqual(len(body["rollouts"]["results"]), 1)
        self.assertEqual(body["rollouts"]["results"][0]["experiment_id"], "automation_route_rollout")

        history_response = self.client.get(
            "/v1/admin/experiments/automation/history",
            params={"limit": 10},
        )
        self.assertEqual(history_response.status_code, 200)
        history_items = history_response.json()
        self.assertGreaterEqual(len(history_items), 1)
        self.assertEqual(history_items[0]["action"], "experiment_automation_run")
        self.assertIn("guardrails", history_items[0]["metadata"])
        self.assertIn("rollouts", history_items[0]["metadata"])


if __name__ == "__main__":
    unittest.main()
