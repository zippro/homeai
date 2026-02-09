from __future__ import annotations

import unittest
from datetime import timedelta
from app.time_utils import utc_now

try:
    from sqlalchemy import delete

    from app.analytics_store import ingest_event
    from app.bootstrap import init_database
    from app.db import session_scope
    from app.experiment_store import (
        assign_active_experiments_for_user,
        assign_experiment,
        evaluate_and_apply_all_experiment_rollouts,
        evaluate_experiment_guardrails,
        get_experiment_performance,
        get_experiment_trends,
        list_experiment_automation_history,
        list_experiments,
        list_experiment_audit,
        run_experiment_automation,
        upsert_experiment,
    )
    from app.models import (
        AdminAuditLogModel,
        AnalyticsEventModel,
        CreditLedgerEntryModel,
        ExperimentAssignmentModel,
        ExperimentModel,
        SubscriptionEntitlementModel,
    )
    from app.schemas import (
        AdminActionRequest,
        AnalyticsEventRequest,
        ExperimentAssignRequest,
        ExperimentUpsertRequest,
        ExperimentVariant,
        JobStatus,
        OperationType,
    )

    _EXPERIMENT_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _EXPERIMENT_TESTS_AVAILABLE = False


@unittest.skipUnless(_EXPERIMENT_TESTS_AVAILABLE, "sqlalchemy dependency is not installed in this environment")
class ExperimentStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()

    def setUp(self) -> None:
        with session_scope() as session:
            session.execute(delete(AnalyticsEventModel))
            session.execute(delete(CreditLedgerEntryModel))
            session.execute(delete(ExperimentAssignmentModel))
            session.execute(delete(ExperimentModel))
            session.execute(delete(SubscriptionEntitlementModel))
            session.execute(delete(AdminAuditLogModel).where(AdminAuditLogModel.domain == "experiments"))

    def test_assign_experiment_is_sticky_for_same_user(self) -> None:
        upsert_experiment(
            experiment_id="pricing_paywall_v1",
            payload=ExperimentUpsertRequest(
                name="Paywall Timing",
                description="Show paywall timing variants",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="upgrade_conversion_7d",
                guardrails={"render_success_rate_min": 85},
                variants=[
                    ExperimentVariant(variant_id="control", weight=50, config={"paywall_mode": "on_exhaustion"}),
                    ExperimentVariant(variant_id="treatment", weight=50, config={"paywall_mode": "after_first_preview"}),
                ],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        first = assign_experiment(ExperimentAssignRequest(experiment_id="pricing_paywall_v1", user_id="u_sticky"))
        second = assign_experiment(ExperimentAssignRequest(experiment_id="pricing_paywall_v1", user_id="u_sticky"))
        other = assign_experiment(ExperimentAssignRequest(experiment_id="pricing_paywall_v1", user_id="u_other"))

        self.assertFalse(first.from_cache)
        self.assertTrue(second.from_cache)
        self.assertEqual(first.variant_id, second.variant_id)
        self.assertIn(first.variant_id, {"control", "treatment"})
        self.assertIn(other.variant_id, {"control", "treatment"})

    def test_assign_active_experiments_returns_assignments(self) -> None:
        upsert_experiment(
            experiment_id="provider_route_v1",
            payload=ExperimentUpsertRequest(
                name="Provider Route",
                description="Provider fallback strategy",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="render_success_rate",
                guardrails={"p95_latency_max_ms": 12000},
                variants=[
                    ExperimentVariant(variant_id="fal_first", weight=60, config={"fallback_chain": "fal,openai"}),
                    ExperimentVariant(variant_id="openai_first", weight=40, config={"fallback_chain": "openai,fal"}),
                ],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        assignments = assign_active_experiments_for_user("u_batch")
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].experiment_id, "provider_route_v1")
        self.assertIn(assignments[0].variant_id, {"fal_first", "openai_first"})

    def test_inactive_experiment_cannot_assign(self) -> None:
        upsert_experiment(
            experiment_id="disabled_experiment",
            payload=ExperimentUpsertRequest(
                name="Disabled",
                description="inactive experiment",
                is_active=False,
                assignment_unit="user_id",
                primary_metric="upgrade_conversion_7d",
                variants=[
                    ExperimentVariant(variant_id="control", weight=100, config={}),
                ],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        with self.assertRaises(ValueError):
            assign_experiment(ExperimentAssignRequest(experiment_id="disabled_experiment", user_id="u_disabled"))

    def test_experiment_audit_is_recorded(self) -> None:
        upsert_experiment(
            experiment_id="audit_exp",
            payload=ExperimentUpsertRequest(
                name="Audit",
                description="audit test",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="upgrade_conversion_7d",
                variants=[ExperimentVariant(variant_id="control", weight=100, config={})],
            ),
            action=AdminActionRequest(actor="qa", reason="record"),
        )
        audit = list_experiment_audit(limit=10)
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0].action, "experiment_upserted")
        self.assertEqual(audit[0].actor, "qa")

    def test_guardrail_evaluator_pauses_experiment_on_breach(self) -> None:
        upsert_experiment(
            experiment_id="guardrail_pause_test",
            payload=ExperimentUpsertRequest(
                name="Guardrail Pause Test",
                description="pause when render success too low",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="render_success_rate",
                guardrails={
                    "render_events_min": 20,
                    "render_success_rate_min": 80,
                },
                variants=[ExperimentVariant(variant_id="control", weight=100, config={})],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        for index in range(25):
            ingest_event(
                AnalyticsEventRequest(
                    event_name="render_status_updated",
                    user_id=f"user_{index}",
                    provider="fal",
                    operation=OperationType.restyle,
                    status=JobStatus.failed,
                    latency_ms=2000,
                    cost_usd=0.02,
                )
            )

        first_result = evaluate_experiment_guardrails(
            hours=24,
            dry_run=False,
            action=AdminActionRequest(actor="tests", reason="enforce"),
        )
        second_result = evaluate_experiment_guardrails(
            hours=24,
            dry_run=False,
            action=AdminActionRequest(actor="tests", reason="enforce"),
        )

        self.assertGreaterEqual(first_result.evaluated_count, 1)
        self.assertGreaterEqual(first_result.breached_count, 1)
        self.assertEqual(first_result.paused_count, 0)
        self.assertGreaterEqual(second_result.paused_count, 1)

        experiments = {item.experiment_id: item for item in list_experiments()}
        self.assertIn("guardrail_pause_test", experiments)
        self.assertFalse(experiments["guardrail_pause_test"].is_active)

        audit = list_experiment_audit(limit=20)
        actions = {item.action for item in audit}
        self.assertIn("experiment_paused_guardrail", actions)

    def test_guardrail_dry_run_does_not_pause(self) -> None:
        upsert_experiment(
            experiment_id="guardrail_dryrun_test",
            payload=ExperimentUpsertRequest(
                name="Guardrail Dry Run",
                description="dry run should not pause",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="render_success_rate",
                guardrails={
                    "render_events_min": 5,
                    "render_success_rate_min": 95,
                },
                variants=[ExperimentVariant(variant_id="control", weight=100, config={})],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        for index in range(10):
            ingest_event(
                AnalyticsEventRequest(
                    event_name="render_status_updated",
                    user_id=f"dry_user_{index}",
                    provider="fal",
                    operation=OperationType.restyle,
                    status=JobStatus.failed,
                )
            )

        result = evaluate_experiment_guardrails(
            hours=24,
            dry_run=True,
            action=AdminActionRequest(actor="tests", reason="dry_run"),
        )

        self.assertGreaterEqual(result.breached_count, 1)
        self.assertEqual(result.paused_count, 0)

        experiments = {item.experiment_id: item for item in list_experiments()}
        self.assertIn("guardrail_dryrun_test", experiments)
        self.assertTrue(experiments["guardrail_dryrun_test"].is_active)

    def test_experiment_performance_recommends_statistically_significant_winner(self) -> None:
        upsert_experiment(
            experiment_id="pricing_perf_test",
            payload=ExperimentUpsertRequest(
                name="Pricing Perf",
                description="performance endpoint",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="upgrade_conversion_7d",
                variants=[
                    ExperimentVariant(variant_id="control", weight=50, config={}),
                    ExperimentVariant(variant_id="treatment", weight=50, config={}),
                ],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        now = utc_now()
        with session_scope() as session:
            for index in range(120):
                user_id = f"perf_control_{index}"
                session.add(
                    ExperimentAssignmentModel(
                        experiment_id="pricing_perf_test",
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
                            original_transaction_id=f"tx_control_{index}",
                            renews_at=None,
                            expires_at=None,
                            metadata_json={},
                            created_at=now,
                            updated_at=now,
                        )
                    )

            for index in range(120):
                user_id = f"perf_treatment_{index}"
                session.add(
                    ExperimentAssignmentModel(
                        experiment_id="pricing_perf_test",
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
                            original_transaction_id=f"tx_treatment_{index}",
                            renews_at=None,
                            expires_at=None,
                            metadata_json={},
                            created_at=now,
                            updated_at=now,
                        )
                    )

        report = get_experiment_performance(experiment_id="pricing_perf_test", hours=24)
        self.assertEqual(report.control_variant_id, "control")
        self.assertEqual(report.recommended_variant_id, "treatment")
        self.assertGreaterEqual(report.total_assigned_users, 240)

        variants = {item.variant_id: item for item in report.variants}
        self.assertIn("control", variants)
        self.assertIn("treatment", variants)
        self.assertAlmostEqual(variants["control"].paid_conversion_rate, 16.67, places=2)
        self.assertAlmostEqual(variants["treatment"].paid_conversion_rate, 40.0, places=2)
        self.assertEqual(variants["control"].paid_source_breakdown.get("web"), 20)
        self.assertEqual(variants["treatment"].paid_source_breakdown.get("ios"), 48)
        self.assertTrue(variants["treatment"].statistically_significant)
        self.assertIsNotNone(variants["treatment"].lift_vs_control_pct)
        self.assertGreater(variants["treatment"].lift_vs_control_pct or 0.0, 0.0)
        self.assertIsNotNone(variants["treatment"].p_value)
        self.assertLess(variants["treatment"].p_value or 1.0, 0.05)

    def test_rollout_state_forces_winner_assignment(self) -> None:
        upsert_experiment(
            experiment_id="rollout_assignment_test",
            payload=ExperimentUpsertRequest(
                name="Rollout Assignment Test",
                description="winner assignment",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="upgrade_conversion_7d",
                variants=[
                    ExperimentVariant(variant_id="control", weight=50, config={}),
                    ExperimentVariant(variant_id="treatment", weight=50, config={}),
                ],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        with session_scope() as session:
            model = session.get(ExperimentModel, "rollout_assignment_test")
            self.assertIsNotNone(model)
            payload_json = dict(model.payload_json or {})
            payload_json["rollout_state"] = {
                "winner_variant_id": "treatment",
                "rollout_percent": 100,
                "status": "rolling_out",
            }
            model.payload_json = payload_json

        chosen_variants = set()
        for index in range(12):
            assignment = assign_experiment(
                ExperimentAssignRequest(
                    experiment_id="rollout_assignment_test",
                    user_id=f"rollout_user_{index}",
                )
            )
            chosen_variants.add(assignment.variant_id)

        self.assertEqual(chosen_variants, {"treatment"})

    def test_experiment_trends_returns_bucketed_variant_metrics(self) -> None:
        upsert_experiment(
            experiment_id="pricing_trend_test",
            payload=ExperimentUpsertRequest(
                name="Pricing Trend",
                description="trend endpoint",
                is_active=True,
                assignment_unit="user_id",
                primary_metric="upgrade_conversion_7d",
                variants=[
                    ExperimentVariant(variant_id="control", weight=50, config={}),
                    ExperimentVariant(variant_id="treatment", weight=50, config={}),
                ],
            ),
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        now = utc_now()
        bucket0_time = now - timedelta(hours=5, minutes=30)
        bucket1_time = now - timedelta(hours=3, minutes=30)

        with session_scope() as session:
            session.add(
                ExperimentAssignmentModel(
                    experiment_id="pricing_trend_test",
                    user_id="trend_control_user",
                    variant_id="control",
                    assigned_at=bucket0_time,
                )
            )
            session.add(
                ExperimentAssignmentModel(
                    experiment_id="pricing_trend_test",
                    user_id="trend_treatment_user",
                    variant_id="treatment",
                    assigned_at=bucket0_time,
                )
            )

            session.add(
                CreditLedgerEntryModel(
                    user_id="trend_control_user",
                    delta=-1,
                    reason="render_preview",
                    idempotency_key=None,
                    metadata_json={},
                    created_at=bucket0_time,
                )
            )
            session.add(
                CreditLedgerEntryModel(
                    user_id="trend_control_user",
                    delta=-2,
                    reason="render_final",
                    idempotency_key=None,
                    metadata_json={},
                    created_at=bucket0_time,
                )
            )
            session.add(
                CreditLedgerEntryModel(
                    user_id="trend_treatment_user",
                    delta=-1,
                    reason="render_preview",
                    idempotency_key=None,
                    metadata_json={},
                    created_at=bucket1_time,
                )
            )

            session.add(
                SubscriptionEntitlementModel(
                    user_id="trend_control_user",
                    plan_id="pro",
                    status="active",
                    source="web",
                    product_id="pro_monthly_web",
                    original_transaction_id="trend_control_tx",
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
                user_id="trend_control_user",
                provider="fal",
                operation=OperationType.restyle,
                status=JobStatus.completed,
                latency_ms=1000,
                cost_usd=0.03,
                occurred_at=bucket0_time,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="checkout_started",
                user_id="trend_control_user",
                provider="fal",
                operation=OperationType.restyle,
                occurred_at=bucket0_time,
            )
        )
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_status_updated",
                user_id="trend_treatment_user",
                provider="fal",
                operation=OperationType.restyle,
                status=JobStatus.failed,
                latency_ms=1500,
                cost_usd=0.02,
                occurred_at=bucket1_time,
            )
        )

        report = get_experiment_trends(
            experiment_id="pricing_trend_test",
            hours=6,
            bucket_hours=2,
        )
        self.assertEqual(report.experiment_id, "pricing_trend_test")
        self.assertEqual(report.window_hours, 6)
        self.assertEqual(report.bucket_hours, 2)
        self.assertEqual(len(report.variants), 2)

        control = next(item for item in report.variants if item.variant_id == "control")
        treatment = next(item for item in report.variants if item.variant_id == "treatment")
        self.assertEqual(len(control.points), 3)
        self.assertEqual(len(treatment.points), 3)

        control_bucket_points = [point for point in control.points if point.render_events > 0]
        self.assertEqual(len(control_bucket_points), 1)
        control_point = control_bucket_points[0]
        self.assertEqual(control_point.render_events, 1)
        self.assertEqual(control_point.preview_users, 1)
        self.assertEqual(control_point.final_users, 1)
        self.assertEqual(control_point.checkout_started_users, 1)
        self.assertEqual(control_point.paid_activations, 1)
        self.assertAlmostEqual(control_point.render_success_rate, 100.0, places=2)

        treatment_bucket_points = [point for point in treatment.points if point.render_events > 0]
        self.assertEqual(len(treatment_bucket_points), 1)
        treatment_point = treatment_bucket_points[0]
        self.assertEqual(treatment_point.render_events, 1)
        self.assertEqual(treatment_point.preview_users, 1)
        self.assertEqual(treatment_point.final_users, 0)
        self.assertAlmostEqual(treatment_point.render_success_rate, 0.0, places=2)

    def test_bulk_rollout_evaluation_returns_summary(self) -> None:
        payload = ExperimentUpsertRequest(
            name="Bulk Rollout",
            description="bulk rollout coverage",
            is_active=True,
            assignment_unit="user_id",
            primary_metric="upgrade_conversion_7d",
            variants=[
                ExperimentVariant(variant_id="control", weight=50, config={}),
                ExperimentVariant(variant_id="treatment", weight=50, config={}),
            ],
        )

        upsert_experiment(
            experiment_id="bulk_rollout_a",
            payload=payload,
            action=AdminActionRequest(actor="tests", reason="setup"),
        )
        upsert_experiment(
            experiment_id="bulk_rollout_b",
            payload=payload,
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        result = evaluate_and_apply_all_experiment_rollouts(
            hours=24,
            dry_run=True,
            action=AdminActionRequest(actor="tests", reason="bulk"),
        )

        self.assertEqual(result.window_hours, 24)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.evaluated_count, 2)
        self.assertEqual(len(result.results), 2)
        self.assertEqual(result.applied_count, 0)
        experiment_ids = {item.experiment_id for item in result.results}
        self.assertEqual(experiment_ids, {"bulk_rollout_a", "bulk_rollout_b"})

    def test_experiment_automation_run_returns_combined_summary(self) -> None:
        payload = ExperimentUpsertRequest(
            name="Automation Rollout",
            description="automation run coverage",
            is_active=True,
            assignment_unit="user_id",
            primary_metric="upgrade_conversion_7d",
            variants=[
                ExperimentVariant(variant_id="control", weight=50, config={}),
                ExperimentVariant(variant_id="treatment", weight=50, config={}),
            ],
        )
        upsert_experiment(
            experiment_id="automation_rollout_a",
            payload=payload,
            action=AdminActionRequest(actor="tests", reason="setup"),
        )

        result = run_experiment_automation(
            hours=24,
            dry_run=True,
            rollout_limit=100,
            action=AdminActionRequest(actor="tests", reason="automation"),
        )
        self.assertTrue(result.dry_run)
        self.assertEqual(result.window_hours, 24)
        self.assertEqual(result.rollout_limit, 100)
        self.assertGreaterEqual(result.guardrails.evaluated_count, 1)
        self.assertEqual(result.rollouts.evaluated_count, 1)
        self.assertEqual(len(result.rollouts.results), 1)
        self.assertEqual(result.rollouts.results[0].experiment_id, "automation_rollout_a")

        automation_history = list_experiment_automation_history(limit=10)
        self.assertEqual(len(automation_history), 1)
        self.assertEqual(automation_history[0].action, "experiment_automation_run")
        self.assertEqual(automation_history[0].actor, "tests")
        metadata = automation_history[0].metadata
        self.assertIsInstance(metadata.get("guardrails"), dict)
        self.assertIsInstance(metadata.get("rollouts"), dict)
        self.assertEqual((metadata.get("rollouts") or {}).get("evaluated_count"), 1)


if __name__ == "__main__":
    unittest.main()
