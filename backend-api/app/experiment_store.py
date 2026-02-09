from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from math import erfc, sqrt
from app.time_utils import utc_now
from typing import Any

from sqlalchemy import delete, desc, select

from app.db import session_scope
from app.models import (
    AdminAuditLogModel,
    AnalyticsEventModel,
    CreditLedgerEntryModel,
    ExperimentAssignmentModel,
    ExperimentModel,
    SubscriptionEntitlementModel,
)
from app.product_store import get_variable_map
from app.schemas import (
    AdminActionRequest,
    AuditLogEntry,
    ExperimentAssignRequest,
    ExperimentAssignResponse,
    ExperimentAutomationRunResponse,
    ExperimentBulkRolloutEvaluationResponse,
    ExperimentConfig,
    ExperimentGuardrailBreach,
    ExperimentGuardrailEvaluation,
    ExperimentGuardrailRunResponse,
    ExperimentPerformanceResponse,
    ExperimentPerformanceVariant,
    ExperimentRolloutEvaluationResponse,
    ExperimentTrendPoint,
    ExperimentTrendResponse,
    ExperimentVariantTrend,
    ExperimentTemplate,
    ExperimentUpsertRequest,
    ExperimentVariant,
    JobStatus,
)

_EXPERIMENT_DOMAIN = "experiments"
_CHECKOUT_EVENTS = {"checkout_started", "web_checkout_started", "checkout_session_started"}
_EXPERIMENT_RUNTIME_KEYS = {
    "guardrail_violation_streak",
    "last_guardrail_checked_at",
    "last_guardrail_breached",
    "last_guardrail_pause",
    "rollout_state",
}
_EXPERIMENT_TEMPLATES: list[ExperimentTemplate] = [
    ExperimentTemplate(
        template_id="pricing_paywall_timing",
        name="Pricing: Paywall Timing",
        description="Compare paywall on exhaustion versus after first successful preview.",
        primary_metric="upgrade_conversion_7d",
        guardrails={
            "render_events_min": 200,
            "render_success_rate_min": 85,
            "p95_latency_max_ms": 12000,
            "avg_cost_per_render_max_usd": 0.15,
        },
        variants=[
            ExperimentVariant(variant_id="control", weight=50, config={"paywall_mode": "on_exhaustion"}),
            ExperimentVariant(variant_id="after_first_preview", weight=50, config={"paywall_mode": "after_first_preview"}),
        ],
    ),
    ExperimentTemplate(
        template_id="pricing_plan_highlight",
        name="Pricing: Plan Highlight",
        description="Test weekly highlighted paywall card versus yearly highlighted card.",
        primary_metric="net_revenue_per_visitor",
        guardrails={
            "render_events_min": 200,
            "paid_conversion_rate_min": 1.0,
            "p95_latency_max_ms": 12000,
        },
        variants=[
            ExperimentVariant(variant_id="weekly_focus", weight=50, config={"default_plan": "weekly"}),
            ExperimentVariant(variant_id="yearly_focus", weight=50, config={"default_plan": "yearly"}),
        ],
    ),
    ExperimentTemplate(
        template_id="provider_preview_quality",
        name="AI: Preview Quality vs Cost",
        description="Compare low-cost preview model against higher-quality preview model.",
        primary_metric="preview_to_final_rate",
        guardrails={
            "render_events_min": 200,
            "render_success_rate_min": 85,
            "avg_cost_per_render_max_usd": 0.15,
            "p95_latency_max_ms": 12000,
        },
        variants=[
            ExperimentVariant(variant_id="cost_optimized", weight=50, config={"preview_quality_tier": "low"}),
            ExperimentVariant(variant_id="quality_optimized", weight=50, config={"preview_quality_tier": "medium"}),
        ],
    ),
    ExperimentTemplate(
        template_id="provider_fallback_order",
        name="AI: Fallback Chain Order",
        description="Evaluate fallback order across providers for success and latency resilience.",
        primary_metric="render_success_rate",
        guardrails={
            "render_events_min": 200,
            "render_success_rate_min": 85,
            "p95_latency_max_ms": 12000,
        },
        variants=[
            ExperimentVariant(variant_id="fal_then_openai", weight=50, config={"fallback_chain": "fal,openai"}),
            ExperimentVariant(variant_id="openai_then_fal", weight=50, config={"fallback_chain": "openai,fal"}),
        ],
    ),
]


def list_experiments(limit: int = 200) -> list[ExperimentConfig]:
    with session_scope() as session:
        stmt = select(ExperimentModel).order_by(desc(ExperimentModel.updated_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [_to_experiment_schema(row) for row in rows]


def list_experiment_templates() -> list[ExperimentTemplate]:
    return [item.model_copy(deep=True) for item in _EXPERIMENT_TEMPLATES]


def upsert_experiment(
    experiment_id: str,
    payload: ExperimentUpsertRequest,
    action: AdminActionRequest,
) -> ExperimentConfig:
    _validate_experiment_payload(payload)

    with session_scope() as session:
        now = utc_now()
        existing = session.get(ExperimentModel, experiment_id)
        payload_json = payload.model_dump(mode="json")
        if existing:
            existing_payload = dict(existing.payload_json or {})
            for runtime_key in _EXPERIMENT_RUNTIME_KEYS:
                if runtime_key in existing_payload and runtime_key not in payload_json:
                    payload_json[runtime_key] = existing_payload[runtime_key]

        if existing:
            existing.payload_json = payload_json
            existing.is_active = payload.is_active
            existing.updated_at = now
            model = existing
        else:
            model = ExperimentModel(
                experiment_id=experiment_id,
                payload_json=payload_json,
                is_active=payload.is_active,
                created_at=now,
                updated_at=now,
            )
            session.add(model)

        _append_audit(
            session=session,
            action="experiment_upserted",
            actor=action.actor,
            reason=action.reason,
            metadata={"experiment_id": experiment_id},
        )
        session.flush()
        session.refresh(model)
        return _to_experiment_schema(model)


def delete_experiment(experiment_id: str, action: AdminActionRequest) -> bool:
    with session_scope() as session:
        existing = session.get(ExperimentModel, experiment_id)
        if not existing:
            return False

        session.execute(
            delete(ExperimentAssignmentModel).where(ExperimentAssignmentModel.experiment_id == experiment_id)
        )
        session.delete(existing)
        _append_audit(
            session=session,
            action="experiment_deleted",
            actor=action.actor,
            reason=action.reason,
            metadata={"experiment_id": experiment_id},
        )
        return True


def list_experiment_audit(limit: int = 100) -> list[AuditLogEntry]:
    with session_scope() as session:
        stmt = (
            select(AdminAuditLogModel)
            .where(AdminAuditLogModel.domain == _EXPERIMENT_DOMAIN)
            .order_by(desc(AdminAuditLogModel.created_at))
            .limit(limit)
        )
        rows = session.execute(stmt).scalars().all()
        return [
            AuditLogEntry(
                id=row.id,
                action=row.action,
                actor=row.actor,
                reason=row.reason,
                created_at=row.created_at,
                metadata=row.metadata_json or {},
            )
            for row in rows
        ]


def list_experiment_automation_history(limit: int = 50) -> list[AuditLogEntry]:
    with session_scope() as session:
        stmt = (
            select(AdminAuditLogModel)
            .where(
                AdminAuditLogModel.domain == _EXPERIMENT_DOMAIN,
                AdminAuditLogModel.action == "experiment_automation_run",
            )
            .order_by(desc(AdminAuditLogModel.created_at))
            .limit(limit)
        )
        rows = session.execute(stmt).scalars().all()
        return [
            AuditLogEntry(
                id=row.id,
                action=row.action,
                actor=row.actor,
                reason=row.reason,
                created_at=row.created_at,
                metadata=row.metadata_json or {},
            )
            for row in rows
        ]


def assign_experiment(payload: ExperimentAssignRequest) -> ExperimentAssignResponse:
    with session_scope() as session:
        experiment = session.get(ExperimentModel, payload.experiment_id)
        if not experiment:
            raise ValueError("experiment_not_found")

        config = _experiment_payload_to_upsert(experiment.payload_json)
        if not experiment.is_active or not config.is_active:
            raise ValueError("experiment_inactive")

        existing_stmt = select(ExperimentAssignmentModel).where(
            ExperimentAssignmentModel.experiment_id == payload.experiment_id,
            ExperimentAssignmentModel.user_id == payload.user_id,
        )
        existing = session.execute(existing_stmt).scalar_one_or_none()
        if existing:
            return _to_assignment_response(
                experiment_id=payload.experiment_id,
                user_id=payload.user_id,
                variant_id=existing.variant_id,
                assigned_at=existing.assigned_at,
                variants=config.variants,
                from_cache=True,
            )

        variant = _pick_variant(
            config.variants,
            payload.experiment_id,
            payload.user_id,
            rollout_state=dict(experiment.payload_json or {}).get("rollout_state"),
        )
        now = utc_now()
        assignment = ExperimentAssignmentModel(
            experiment_id=payload.experiment_id,
            user_id=payload.user_id,
            variant_id=variant.variant_id,
            assigned_at=now,
        )
        session.add(assignment)

        return _to_assignment_response(
            experiment_id=payload.experiment_id,
            user_id=payload.user_id,
            variant_id=variant.variant_id,
            assigned_at=now,
            variants=config.variants,
            from_cache=False,
        )


def assign_active_experiments_for_user(user_id: str, limit: int = 50) -> list[ExperimentAssignResponse]:
    with session_scope() as session:
        experiments_stmt = (
            select(ExperimentModel)
            .where(ExperimentModel.is_active.is_(True))
            .order_by(desc(ExperimentModel.updated_at))
            .limit(limit)
        )
        experiments = session.execute(experiments_stmt).scalars().all()
        assignments: list[ExperimentAssignResponse] = []
        now = utc_now()

        for experiment in experiments:
            config = _experiment_payload_to_upsert(experiment.payload_json)
            if not config.is_active:
                continue

            existing_stmt = select(ExperimentAssignmentModel).where(
                ExperimentAssignmentModel.experiment_id == experiment.experiment_id,
                ExperimentAssignmentModel.user_id == user_id,
            )
            existing = session.execute(existing_stmt).scalar_one_or_none()
            if existing:
                assignments.append(
                    _to_assignment_response(
                        experiment_id=experiment.experiment_id,
                        user_id=user_id,
                        variant_id=existing.variant_id,
                        assigned_at=existing.assigned_at,
                        variants=config.variants,
                        from_cache=True,
                    )
                )
                continue

            variant = _pick_variant(
                config.variants,
                experiment.experiment_id,
                user_id,
                rollout_state=dict(experiment.payload_json or {}).get("rollout_state"),
            )
            assignment = ExperimentAssignmentModel(
                experiment_id=experiment.experiment_id,
                user_id=user_id,
                variant_id=variant.variant_id,
                assigned_at=now,
            )
            session.add(assignment)
            assignments.append(
                _to_assignment_response(
                    experiment_id=experiment.experiment_id,
                    user_id=user_id,
                    variant_id=variant.variant_id,
                    assigned_at=now,
                    variants=config.variants,
                    from_cache=False,
                )
            )

        return assignments


def evaluate_experiment_guardrails(
    *,
    hours: int,
    dry_run: bool,
    action: AdminActionRequest,
) -> ExperimentGuardrailRunResponse:
    # Local import avoids circular dependency (analytics imports experiment models).
    from app.analytics_store import get_analytics_dashboard

    checked_at = utc_now()
    window_hours = max(1, int(hours))
    dashboard = get_analytics_dashboard(hours=window_hours)
    experiment_metrics = {item.experiment_id: item for item in dashboard.experiment_breakdown}
    variables = get_variable_map()
    required_streak_raw = _safe_float(variables.get("experiment_guardrail_consecutive_runs_required"))
    required_streak = max(1, int(required_streak_raw if required_streak_raw is not None else 2))

    evaluations: list[ExperimentGuardrailEvaluation] = []
    breached_count = 0
    paused_count = 0

    with session_scope() as session:
        stmt = select(ExperimentModel).order_by(desc(ExperimentModel.updated_at)).limit(1000)
        models = session.execute(stmt).scalars().all()

        for model in models:
            config = _to_experiment_schema(model)
            guardrails = dict(config.guardrails or {})
            metric = experiment_metrics.get(config.experiment_id)
            payload_state = dict(model.payload_json or {})
            current_streak = int(payload_state.get("guardrail_violation_streak", 0) or 0)

            skipped_reason = _guardrail_skip_reason(
                guardrails=guardrails,
                dashboard=dashboard,
                experiment_metric=metric,
            )
            if skipped_reason:
                evaluations.append(
                    ExperimentGuardrailEvaluation(
                        experiment_id=config.experiment_id,
                        name=config.name,
                        is_active=bool(model.is_active),
                        breached=False,
                        paused=False,
                        violation_streak=current_streak,
                        required_streak=required_streak,
                        skipped=True,
                        skipped_reason=skipped_reason,
                        breach_count=0,
                        guardrails=guardrails,
                        breaches=[],
                    )
                )
                continue

            breaches = _evaluate_guardrail_breaches(
                guardrails=guardrails,
                dashboard=dashboard,
                experiment_metric=metric,
            )

            breached = len(breaches) > 0
            paused = False
            if breached:
                breached_count += 1
            next_streak = current_streak + 1 if breached else 0

            should_pause = breached and bool(model.is_active) and next_streak >= required_streak

            if not dry_run:
                payload_state["guardrail_violation_streak"] = next_streak
                payload_state["last_guardrail_checked_at"] = checked_at.isoformat()
                payload_state["last_guardrail_breached"] = breached

                if should_pause:
                    paused = True
                    paused_count += 1
                    payload_state["is_active"] = False
                    payload_state["last_guardrail_pause"] = {
                        "paused_at": checked_at.isoformat(),
                        "window_hours": window_hours,
                        "breach_count": len(breaches),
                        "required_streak": required_streak,
                        "violation_streak": next_streak,
                    }
                    model.is_active = False

                    _append_audit(
                        session=session,
                        action="experiment_paused_guardrail",
                        actor=action.actor,
                        reason=action.reason or "guardrail_enforcement",
                        metadata={
                            "experiment_id": config.experiment_id,
                            "window_hours": window_hours,
                            "required_streak": required_streak,
                            "violation_streak": next_streak,
                            "breaches": [item.model_dump(mode="json") for item in breaches],
                        },
                    )

                model.payload_json = payload_state
                model.updated_at = checked_at
            else:
                paused = should_pause

            evaluations.append(
                ExperimentGuardrailEvaluation(
                    experiment_id=config.experiment_id,
                    name=config.name,
                    is_active=bool(model.is_active),
                    breached=breached,
                    paused=paused,
                    violation_streak=next_streak,
                    required_streak=required_streak,
                    skipped=False,
                    skipped_reason=None,
                    breach_count=len(breaches),
                    guardrails=guardrails,
                    breaches=breaches,
                )
            )

    return ExperimentGuardrailRunResponse(
        checked_at=checked_at,
        window_hours=window_hours,
        dry_run=dry_run,
        required_streak=required_streak,
        evaluated_count=len(evaluations),
        breached_count=breached_count,
        paused_count=paused_count,
        evaluations=evaluations,
    )


def get_experiment_performance(*, experiment_id: str, hours: int) -> ExperimentPerformanceResponse:
    generated_at = utc_now()
    window_hours = max(1, int(hours))
    window_start = generated_at - timedelta(hours=window_hours)

    with session_scope() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        if not experiment:
            raise ValueError("experiment_not_found")

        config = _to_experiment_schema(experiment)
        assignment_stmt = select(ExperimentAssignmentModel).where(
            ExperimentAssignmentModel.experiment_id == experiment_id
        )
        assignment_rows = session.execute(assignment_stmt).scalars().all()

        users_by_variant: dict[str, set[str]] = {}
        for row in assignment_rows:
            users_by_variant.setdefault(row.variant_id, set()).add(row.user_id)

        configured_variant_ids = [item.variant_id for item in config.variants]
        variant_ids = list(dict.fromkeys(configured_variant_ids + sorted(users_by_variant.keys())))
        all_user_ids = set().union(*users_by_variant.values()) if users_by_variant else set()

        if all_user_ids:
            event_stmt = (
                select(AnalyticsEventModel)
                .where(
                    AnalyticsEventModel.user_id.in_(all_user_ids),
                    AnalyticsEventModel.occurred_at >= window_start,
                )
                .order_by(AnalyticsEventModel.id)
            )
            events = session.execute(event_stmt).scalars().all()

            ledger_stmt = select(CreditLedgerEntryModel).where(
                CreditLedgerEntryModel.user_id.in_(all_user_ids),
                CreditLedgerEntryModel.created_at >= window_start,
            )
            ledger_rows = session.execute(ledger_stmt).scalars().all()

            active_subscription_stmt = select(SubscriptionEntitlementModel).where(
                SubscriptionEntitlementModel.user_id.in_(all_user_ids),
                SubscriptionEntitlementModel.status == "active",
            )
            active_subscriptions = session.execute(active_subscription_stmt).scalars().all()
        else:
            events = []
            ledger_rows = []
            active_subscriptions = []

    active_paid_user_ids = {item.user_id for item in active_subscriptions}
    paid_source_by_user = {item.user_id: (item.source or "unknown") for item in active_subscriptions}

    events_by_user: dict[str, list[AnalyticsEventModel]] = {}
    for row in events:
        if row.user_id:
            events_by_user.setdefault(row.user_id, []).append(row)

    ledger_by_user: dict[str, list[CreditLedgerEntryModel]] = {}
    for row in ledger_rows:
        ledger_by_user.setdefault(row.user_id, []).append(row)

    variables = get_variable_map()
    significance_alpha = _bounded_float(
        _safe_float(variables.get("experiment_significance_alpha")),
        default=0.05,
        min_value=0.001,
        max_value=0.2,
    )
    minimum_sample_size = max(
        10,
        int(_safe_float(variables.get("experiment_primary_metric_min_sample_size")) or 100),
    )

    control_variant_id = _resolve_control_variant_id(
        variant_ids=variant_ids,
        configured_variant_ids=configured_variant_ids,
    )

    variant_rows: list[ExperimentPerformanceVariant] = []
    primary_counts_by_variant: dict[str, tuple[int, int, float]] = {}
    total_assigned_users = 0

    for variant_id in variant_ids:
        assigned_users = users_by_variant.get(variant_id, set())
        total_assigned_users += len(assigned_users)
        checkout_started_users_set: set[str] = set()
        render_events_rows: list[AnalyticsEventModel] = []

        preview_users = 0
        final_users = 0
        for user_id in assigned_users:
            user_events = events_by_user.get(user_id, [])
            for row in user_events:
                if row.event_name in _CHECKOUT_EVENTS:
                    checkout_started_users_set.add(user_id)
                if row.event_name.startswith("render_"):
                    render_events_rows.append(row)

            user_ledger_rows = ledger_by_user.get(user_id, [])
            has_preview = any(item.delta < 0 and item.reason == "render_preview" for item in user_ledger_rows)
            has_final = any(item.delta < 0 and item.reason == "render_final" for item in user_ledger_rows)
            if has_preview:
                preview_users += 1
            if has_final:
                final_users += 1

        render_events = len(render_events_rows)
        render_success = sum(1 for row in render_events_rows if row.status == JobStatus.completed.value)
        latencies = [row.latency_ms for row in render_events_rows if row.latency_ms is not None]
        total_cost = sum(float(row.cost_usd) for row in render_events_rows if row.cost_usd is not None)
        active_paid_users = len(assigned_users & active_paid_user_ids)
        checkout_started_users = len(checkout_started_users_set)
        paid_source_breakdown: dict[str, int] = {}
        for user_id in (assigned_users & active_paid_user_ids):
            source = paid_source_by_user.get(user_id, "unknown")
            paid_source_breakdown[source] = paid_source_breakdown.get(source, 0) + 1

        primary_metric_value, primary_successes, primary_trials = _primary_metric_counts(
            metric_key=config.primary_metric,
            assigned_users=len(assigned_users),
            active_paid_users=active_paid_users,
            checkout_started_users=checkout_started_users,
            preview_users=preview_users,
            final_users=final_users,
            render_events=render_events,
            render_success=render_success,
        )

        primary_counts_by_variant[variant_id] = (primary_successes, primary_trials, primary_metric_value)
        variant_rows.append(
            ExperimentPerformanceVariant(
                variant_id=variant_id,
                assigned_users=len(assigned_users),
                active_paid_users=active_paid_users,
                paid_conversion_rate=_rate(active_paid_users, len(assigned_users)),
                checkout_started_users=checkout_started_users,
                checkout_start_rate=_rate(checkout_started_users, len(assigned_users)),
                preview_users=preview_users,
                final_users=final_users,
                preview_to_final_rate=_rate(final_users, preview_users),
                render_events=render_events,
                render_success_rate=_rate(render_success, render_events),
                avg_latency_ms=_rounded(_avg(latencies)),
                p95_latency_ms=_rounded(_percentile(latencies, 0.95) if latencies else None),
                total_cost_usd=round(total_cost, 6),
                avg_cost_usd=_rounded(total_cost / render_events if render_events else None),
                primary_metric_value=primary_metric_value,
                paid_source_breakdown=dict(sorted(paid_source_breakdown.items())),
                primary_metric_successes=primary_successes if primary_trials > 0 else None,
                primary_metric_trials=primary_trials if primary_trials > 0 else None,
            )
        )

    if control_variant_id and control_variant_id in primary_counts_by_variant:
        control_successes, control_trials, control_metric = primary_counts_by_variant[control_variant_id]
        for item in variant_rows:
            if item.variant_id == control_variant_id:
                continue
            success, trials, metric_value = primary_counts_by_variant.get(item.variant_id, (0, 0, 0.0))
            item.lift_vs_control_pct = _lift_pct(metric_value, control_metric)
            p_value = _proportion_p_value(
                success_a=control_successes,
                trials_a=control_trials,
                success_b=success,
                trials_b=trials,
            )
            item.p_value = round(p_value, 4) if p_value is not None else None
            item.statistically_significant = bool(p_value is not None and p_value < significance_alpha)

    recommended_variant_id, recommendation_reason = _recommend_variant(
        variants=variant_rows,
        control_variant_id=control_variant_id,
        primary_metric=config.primary_metric,
        minimum_sample_size=minimum_sample_size,
    )

    return ExperimentPerformanceResponse(
        experiment_id=config.experiment_id,
        name=config.name,
        primary_metric=config.primary_metric,
        generated_at=generated_at,
        window_hours=window_hours,
        control_variant_id=control_variant_id,
        significance_alpha=significance_alpha,
        minimum_sample_size=minimum_sample_size,
        total_assigned_users=total_assigned_users,
        recommended_variant_id=recommended_variant_id,
        recommendation_reason=recommendation_reason,
        variants=variant_rows,
    )


def get_experiment_trends(*, experiment_id: str, hours: int, bucket_hours: int) -> ExperimentTrendResponse:
    generated_at = utc_now()
    window_hours = max(1, int(hours))
    bucket_hours_value = max(1, int(bucket_hours))
    window_start = generated_at - timedelta(hours=window_hours)
    windows = _build_bucket_windows(
        window_start=window_start,
        window_end=generated_at,
        bucket_hours=bucket_hours_value,
    )

    with session_scope() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        if not experiment:
            raise ValueError("experiment_not_found")

        config = _to_experiment_schema(experiment)
        assignment_stmt = select(ExperimentAssignmentModel).where(
            ExperimentAssignmentModel.experiment_id == experiment_id
        )
        assignment_rows = session.execute(assignment_stmt).scalars().all()

        users_by_variant: dict[str, set[str]] = defaultdict(set)
        assigned_at_by_user: dict[str, datetime] = {}
        variant_by_user: dict[str, str] = {}
        assignments_by_variant: dict[str, list[ExperimentAssignmentModel]] = defaultdict(list)
        for row in assignment_rows:
            users_by_variant[row.variant_id].add(row.user_id)
            assignments_by_variant[row.variant_id].append(row)
            assigned_at_by_user[row.user_id] = row.assigned_at
            variant_by_user[row.user_id] = row.variant_id

        configured_variant_ids = [item.variant_id for item in config.variants]
        variant_ids = list(dict.fromkeys(configured_variant_ids + sorted(users_by_variant.keys())))
        all_user_ids = set(variant_by_user.keys())

        if all_user_ids:
            event_stmt = (
                select(AnalyticsEventModel)
                .where(
                    AnalyticsEventModel.user_id.in_(all_user_ids),
                    AnalyticsEventModel.occurred_at >= window_start,
                )
                .order_by(AnalyticsEventModel.id)
            )
            events = session.execute(event_stmt).scalars().all()

            ledger_stmt = select(CreditLedgerEntryModel).where(
                CreditLedgerEntryModel.user_id.in_(all_user_ids),
                CreditLedgerEntryModel.created_at >= window_start,
            )
            ledger_rows = session.execute(ledger_stmt).scalars().all()

            active_subscription_stmt = select(SubscriptionEntitlementModel).where(
                SubscriptionEntitlementModel.user_id.in_(all_user_ids),
                SubscriptionEntitlementModel.status == "active",
            )
            active_subscriptions = session.execute(active_subscription_stmt).scalars().all()
        else:
            events = []
            ledger_rows = []
            active_subscriptions = []

    control_variant_id = _resolve_control_variant_id(
        variant_ids=variant_ids,
        configured_variant_ids=configured_variant_ids,
    )

    events_by_variant_bucket: dict[str, list[dict[str, Any]]] = {
        variant_id: [_new_bucket_accumulator() for _ in windows]
        for variant_id in variant_ids
    }
    active_paid_updated_at_by_variant: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
    for row in active_subscriptions:
        variant_id = variant_by_user.get(row.user_id)
        if not variant_id:
            continue
        assigned_at = assigned_at_by_user.get(row.user_id)
        if assigned_at and row.updated_at < assigned_at:
            continue
        active_paid_updated_at_by_variant[variant_id].append((row.user_id, row.updated_at))

    for row in events:
        user_id = row.user_id
        if not user_id:
            continue
        variant_id = variant_by_user.get(user_id)
        if not variant_id:
            continue
        assigned_at = assigned_at_by_user.get(user_id)
        if assigned_at and row.occurred_at < assigned_at:
            continue
        bucket_index = _bucket_index(
            timestamp=row.occurred_at,
            window_start=window_start,
            bucket_hours=bucket_hours_value,
            bucket_count=len(windows),
        )
        if bucket_index is None:
            continue
        bucket = events_by_variant_bucket[variant_id][bucket_index]

        if row.event_name.startswith("render_"):
            bucket["render_events"] += 1
            if row.status == JobStatus.completed.value:
                bucket["render_success"] += 1
            if row.latency_ms is not None:
                bucket["latencies"].append(int(row.latency_ms))
            if row.cost_usd is not None:
                bucket["total_cost_usd"] += float(row.cost_usd)

        if row.event_name in _CHECKOUT_EVENTS:
            bucket["checkout_users"].add(user_id)

    for row in ledger_rows:
        variant_id = variant_by_user.get(row.user_id)
        if not variant_id:
            continue
        assigned_at = assigned_at_by_user.get(row.user_id)
        if assigned_at and row.created_at < assigned_at:
            continue
        bucket_index = _bucket_index(
            timestamp=row.created_at,
            window_start=window_start,
            bucket_hours=bucket_hours_value,
            bucket_count=len(windows),
        )
        if bucket_index is None:
            continue
        bucket = events_by_variant_bucket[variant_id][bucket_index]
        if row.delta < 0 and row.reason == "render_preview":
            bucket["preview_users"].add(row.user_id)
        if row.delta < 0 and row.reason == "render_final":
            bucket["final_users"].add(row.user_id)

    for row in active_subscriptions:
        variant_id = variant_by_user.get(row.user_id)
        if not variant_id:
            continue
        assigned_at = assigned_at_by_user.get(row.user_id)
        if assigned_at and row.updated_at < assigned_at:
            continue
        bucket_index = _bucket_index(
            timestamp=row.updated_at,
            window_start=window_start,
            bucket_hours=bucket_hours_value,
            bucket_count=len(windows),
        )
        if bucket_index is None:
            continue
        bucket = events_by_variant_bucket[variant_id][bucket_index]
        bucket["paid_activation_users"].add(row.user_id)

    variant_trends: list[ExperimentVariantTrend] = []
    for variant_id in variant_ids:
        assignment_rows_for_variant = sorted(
            assignments_by_variant.get(variant_id, []),
            key=lambda item: (item.assigned_at, item.id),
        )
        assignment_cursor = 0
        assigned_users_cumulative: set[str] = set()
        active_paid_rows = active_paid_updated_at_by_variant.get(variant_id, [])
        points: list[ExperimentTrendPoint] = []

        for idx, (bucket_start, bucket_end) in enumerate(windows):
            while assignment_cursor < len(assignment_rows_for_variant):
                assignment_row = assignment_rows_for_variant[assignment_cursor]
                if assignment_row.assigned_at >= bucket_end:
                    break
                assigned_users_cumulative.add(assignment_row.user_id)
                assignment_cursor += 1

            assigned_users = len(assigned_users_cumulative)
            bucket = events_by_variant_bucket[variant_id][idx]

            render_events = int(bucket["render_events"])
            render_success = int(bucket["render_success"])
            latencies = list(bucket["latencies"])
            preview_users = len(bucket["preview_users"])
            final_users = len(bucket["final_users"])
            checkout_started_users = len(bucket["checkout_users"])
            paid_activations = len(bucket["paid_activation_users"])
            active_paid_users = sum(
                1
                for user_id, updated_at in active_paid_rows
                if updated_at < bucket_end and user_id in assigned_users_cumulative
            )

            primary_metric_value, _, _ = _primary_metric_counts(
                metric_key=config.primary_metric,
                assigned_users=assigned_users,
                active_paid_users=active_paid_users,
                checkout_started_users=checkout_started_users,
                preview_users=preview_users,
                final_users=final_users,
                render_events=render_events,
                render_success=render_success,
            )

            points.append(
                ExperimentTrendPoint(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end,
                    assigned_users=assigned_users,
                    render_events=render_events,
                    render_success_rate=_rate(render_success, render_events),
                    avg_latency_ms=_rounded(_avg(latencies)),
                    total_cost_usd=round(float(bucket["total_cost_usd"]), 6),
                    preview_users=preview_users,
                    final_users=final_users,
                    preview_to_final_rate=_rate(final_users, preview_users),
                    checkout_started_users=checkout_started_users,
                    paid_activations=paid_activations,
                    paid_activation_rate=_rate(paid_activations, checkout_started_users),
                    primary_metric_value=primary_metric_value,
                )
            )

        variant_trends.append(
            ExperimentVariantTrend(
                variant_id=variant_id,
                points=points,
            )
        )

    return ExperimentTrendResponse(
        experiment_id=config.experiment_id,
        name=config.name,
        primary_metric=config.primary_metric,
        generated_at=generated_at,
        window_hours=window_hours,
        bucket_hours=bucket_hours_value,
        control_variant_id=control_variant_id,
        variants=variant_trends,
    )


def evaluate_and_apply_experiment_rollout(
    *,
    experiment_id: str,
    hours: int,
    dry_run: bool,
    action: AdminActionRequest,
) -> ExperimentRolloutEvaluationResponse:
    checked_at = utc_now()
    window_hours = max(1, int(hours))
    performance = get_experiment_performance(experiment_id=experiment_id, hours=window_hours)

    guardrail_run = evaluate_experiment_guardrails(
        hours=window_hours,
        dry_run=True,
        action=AdminActionRequest(actor=f"{action.actor}:rollout-check", reason=action.reason),
    )
    guardrail_eval = next(
        (item for item in guardrail_run.evaluations if item.experiment_id == experiment_id),
        None,
    )
    guardrails_clear = bool(guardrail_eval and not guardrail_eval.breached and not guardrail_eval.skipped)

    with session_scope() as session:
        model = session.get(ExperimentModel, experiment_id)
        if not model:
            raise ValueError("experiment_not_found")

        payload_state = dict(model.payload_json or {})
        rollout_state = dict(payload_state.get("rollout_state") or {})
        current_rollout_percent = _extract_rollout_percent(rollout_state)
        next_rollout_percent = _next_rollout_percent(current_rollout_percent)
        rollout_status = str(rollout_state.get("status") or "holding")
        winner_variant_id = performance.recommended_variant_id

        blocked_reason: str | None = None
        if not bool(model.is_active):
            blocked_reason = "experiment_inactive"
        elif winner_variant_id is None:
            blocked_reason = "no_winner_recommendation"
        elif performance.control_variant_id and winner_variant_id == performance.control_variant_id:
            blocked_reason = "control_is_winner"
        elif not guardrails_clear:
            if guardrail_eval and guardrail_eval.skipped:
                blocked_reason = f"guardrail_skipped:{guardrail_eval.skipped_reason or 'insufficient_sample'}"
            else:
                blocked_reason = "guardrail_breached"
        elif current_rollout_percent >= 100:
            blocked_reason = "already_full_rollout"
        elif next_rollout_percent <= current_rollout_percent:
            blocked_reason = "no_rollout_step_available"

        applied = False
        if blocked_reason is None:
            rollout_status = "completed" if next_rollout_percent >= 100 else "rolling_out"
            if not dry_run:
                history = list(rollout_state.get("history") or [])
                history.append(
                    {
                        "at": checked_at.isoformat(),
                        "from_percent": current_rollout_percent,
                        "to_percent": next_rollout_percent,
                        "winner_variant_id": winner_variant_id,
                        "actor": action.actor,
                        "reason": action.reason or "rollout_evaluate",
                    }
                )

                rollout_state = {
                    **rollout_state,
                    "winner_variant_id": winner_variant_id,
                    "rollout_percent": next_rollout_percent,
                    "status": rollout_status,
                    "last_action_at": checked_at.isoformat(),
                    "last_reason": action.reason or "rollout_evaluate",
                    "history": history[-20:],
                }
                payload_state["rollout_state"] = rollout_state
                model.payload_json = payload_state
                model.updated_at = checked_at
                applied = True

                _append_audit(
                    session=session,
                    action="experiment_rollout_applied",
                    actor=action.actor,
                    reason=action.reason,
                    metadata={
                        "experiment_id": experiment_id,
                        "winner_variant_id": winner_variant_id,
                        "from_percent": current_rollout_percent,
                        "to_percent": next_rollout_percent,
                        "window_hours": window_hours,
                        "recommendation_reason": performance.recommendation_reason,
                    },
                )

    return ExperimentRolloutEvaluationResponse(
        experiment_id=experiment_id,
        checked_at=checked_at,
        dry_run=dry_run,
        window_hours=window_hours,
        winner_variant_id=winner_variant_id,
        recommendation_reason=performance.recommendation_reason,
        guardrails_clear=guardrails_clear,
        blocked_reason=blocked_reason,
        current_rollout_percent=current_rollout_percent,
        next_rollout_percent=next_rollout_percent,
        rollout_status=rollout_status,
        applied=applied,
        performance_total_assigned_users=performance.total_assigned_users,
        minimum_sample_size=performance.minimum_sample_size,
        significance_alpha=performance.significance_alpha,
    )


def evaluate_and_apply_all_experiment_rollouts(
    *,
    hours: int,
    dry_run: bool,
    action: AdminActionRequest,
    limit: int = 200,
) -> ExperimentBulkRolloutEvaluationResponse:
    checked_at = utc_now()
    window_hours = max(1, int(hours))
    max_experiments = max(1, min(1000, int(limit)))

    with session_scope() as session:
        stmt = (
            select(ExperimentModel.experiment_id)
            .where(ExperimentModel.is_active.is_(True))
            .order_by(desc(ExperimentModel.updated_at))
            .limit(max_experiments)
        )
        experiment_ids = [row[0] for row in session.execute(stmt).all()]

    results: list[ExperimentRolloutEvaluationResponse] = []
    for experiment_id in experiment_ids:
        result = evaluate_and_apply_experiment_rollout(
            experiment_id=experiment_id,
            hours=window_hours,
            dry_run=dry_run,
            action=action,
        )
        results.append(result)

    applied_count = sum(1 for item in results if item.applied)
    blocked_count = sum(1 for item in results if item.blocked_reason is not None)

    return ExperimentBulkRolloutEvaluationResponse(
        checked_at=checked_at,
        dry_run=dry_run,
        window_hours=window_hours,
        evaluated_count=len(results),
        applied_count=applied_count,
        blocked_count=blocked_count,
        results=results,
    )


def run_experiment_automation(
    *,
    hours: int,
    dry_run: bool,
    rollout_limit: int,
    action: AdminActionRequest,
) -> ExperimentAutomationRunResponse:
    checked_at = utc_now()
    window_hours = max(1, int(hours))
    capped_rollout_limit = max(1, min(1000, int(rollout_limit)))

    guardrail_result = evaluate_experiment_guardrails(
        hours=window_hours,
        dry_run=dry_run,
        action=AdminActionRequest(
            actor=f"{action.actor}:automation-guardrails",
            reason=action.reason or "automation_run",
        ),
    )
    rollout_result = evaluate_and_apply_all_experiment_rollouts(
        hours=window_hours,
        dry_run=dry_run,
        limit=capped_rollout_limit,
        action=AdminActionRequest(
            actor=f"{action.actor}:automation-rollouts",
            reason=action.reason or "automation_run",
        ),
    )

    with session_scope() as session:
        _append_audit(
            session=session,
            action="experiment_automation_run",
            actor=action.actor,
            reason=action.reason,
            metadata={
                "checked_at": checked_at.isoformat(),
                "dry_run": dry_run,
                "window_hours": window_hours,
                "rollout_limit": capped_rollout_limit,
                "guardrails": {
                    "evaluated_count": guardrail_result.evaluated_count,
                    "breached_count": guardrail_result.breached_count,
                    "paused_count": guardrail_result.paused_count,
                },
                "rollouts": {
                    "evaluated_count": rollout_result.evaluated_count,
                    "applied_count": rollout_result.applied_count,
                    "blocked_count": rollout_result.blocked_count,
                    "applied_experiment_ids": [
                        item.experiment_id for item in rollout_result.results if item.applied
                    ][:100],
                    "blocked_experiment_ids": [
                        item.experiment_id for item in rollout_result.results if item.blocked_reason is not None
                    ][:100],
                },
            },
        )

    return ExperimentAutomationRunResponse(
        checked_at=checked_at,
        dry_run=dry_run,
        window_hours=window_hours,
        rollout_limit=capped_rollout_limit,
        guardrails=guardrail_result,
        rollouts=rollout_result,
    )


def _validate_experiment_payload(payload: ExperimentUpsertRequest) -> None:
    if payload.assignment_unit != "user_id":
        raise ValueError("unsupported_assignment_unit")
    if not payload.primary_metric.strip():
        raise ValueError("primary_metric_required")
    if not payload.variants:
        raise ValueError("at_least_one_variant_required")

    total_weight = 0
    seen_variant_ids: set[str] = set()
    for variant in payload.variants:
        variant_id = variant.variant_id.strip()
        if not variant_id:
            raise ValueError("variant_id_required")
        if variant_id in seen_variant_ids:
            raise ValueError("duplicate_variant_id")
        seen_variant_ids.add(variant_id)
        total_weight += int(variant.weight)

    if total_weight <= 0:
        raise ValueError("variant_weight_total_must_be_positive")


def _pick_variant(
    variants: list[ExperimentVariant],
    experiment_id: str,
    user_id: str,
    rollout_state: Any | None = None,
) -> ExperimentVariant:
    total_weight = sum(max(0, int(item.weight)) for item in variants)
    if total_weight <= 0:
        raise ValueError("variant_weight_total_must_be_positive")

    rollout = dict(rollout_state or {})
    winner_variant_id = str(rollout.get("winner_variant_id") or "").strip()
    rollout_percent = _extract_rollout_percent(rollout)
    variant_map = {variant.variant_id: variant for variant in variants}
    winner = variant_map.get(winner_variant_id)

    if winner and rollout_percent > 0:
        rollout_bucket = _stable_bucket(experiment_id=experiment_id, user_id=user_id, salt="rollout", modulo=100)
        if rollout_bucket < rollout_percent:
            return winner

        baseline_variants = [variant for variant in variants if variant.variant_id != winner_variant_id]
        if baseline_variants:
            return _pick_weighted_variant(
                variants=baseline_variants,
                experiment_id=experiment_id,
                user_id=user_id,
                salt="baseline",
            )
        return winner

    return _pick_weighted_variant(
        variants=variants,
        experiment_id=experiment_id,
        user_id=user_id,
        salt="default",
    )


def _pick_weighted_variant(
    *,
    variants: list[ExperimentVariant],
    experiment_id: str,
    user_id: str,
    salt: str,
) -> ExperimentVariant:
    total_weight = sum(max(0, int(item.weight)) for item in variants)
    if total_weight <= 0:
        raise ValueError("variant_weight_total_must_be_positive")

    bucket = _stable_bucket(experiment_id=experiment_id, user_id=user_id, salt=salt, modulo=total_weight)
    cumulative = 0
    for variant in variants:
        cumulative += int(variant.weight)
        if bucket < cumulative:
            return variant
    return variants[-1]


def _stable_bucket(*, experiment_id: str, user_id: str, salt: str, modulo: int) -> int:
    key = f"{experiment_id}:{user_id}:{salt}"
    hashed = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    return hashed % max(1, modulo)


def _to_assignment_response(
    *,
    experiment_id: str,
    user_id: str,
    variant_id: str,
    assigned_at: datetime,
    variants: list[ExperimentVariant],
    from_cache: bool,
) -> ExperimentAssignResponse:
    config_map = {variant.variant_id: variant.config for variant in variants}
    return ExperimentAssignResponse(
        experiment_id=experiment_id,
        user_id=user_id,
        variant_id=variant_id,
        config=config_map.get(variant_id, {}),
        assigned_at=assigned_at,
        from_cache=from_cache,
    )


def _experiment_payload_to_upsert(payload: dict) -> ExperimentUpsertRequest:
    try:
        model = ExperimentUpsertRequest.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid_experiment_payload:{exc}") from exc
    _validate_experiment_payload(model)
    return model


def _to_experiment_schema(model: ExperimentModel) -> ExperimentConfig:
    payload = dict(model.payload_json or {})
    return ExperimentConfig(
        experiment_id=model.experiment_id,
        name=str(payload.get("name") or model.experiment_id),
        description=payload.get("description"),
        is_active=bool(payload.get("is_active", model.is_active)),
        assignment_unit=str(payload.get("assignment_unit") or "user_id"),
        primary_metric=str(payload.get("primary_metric") or "conversion"),
        guardrails=dict(payload.get("guardrails") or {}),
        variants=[ExperimentVariant.model_validate(item) for item in payload.get("variants", [])],
        rollout_state=dict(payload.get("rollout_state") or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _append_audit(
    session,
    action: str,
    actor: str,
    reason: str | None,
    metadata: dict,
) -> None:
    entry = AuditLogEntry(
        action=action,
        actor=actor,
        reason=reason,
        metadata=metadata,
    )
    session.add(
        AdminAuditLogModel(
            id=entry.id,
            domain=_EXPERIMENT_DOMAIN,
            action=entry.action,
            actor=entry.actor,
            reason=entry.reason,
            metadata_json=entry.metadata,
            created_at=entry.created_at,
        )
    )


def _guardrail_skip_reason(*, guardrails: dict[str, Any], dashboard, experiment_metric) -> str | None:
    render_events_min = _guardrail_number(guardrails, "render_events_min")
    if render_events_min is not None and dashboard.summary.render_events < render_events_min:
        return f"render_events_below_min({dashboard.summary.render_events} < {render_events_min})"

    assigned_users_min = _guardrail_number(guardrails, "total_assigned_users_min")
    assigned_users = float(experiment_metric.total_assigned_users) if experiment_metric else 0.0
    if assigned_users_min is not None and assigned_users < assigned_users_min:
        return f"assigned_users_below_min({assigned_users} < {assigned_users_min})"

    return None


def _evaluate_guardrail_breaches(
    *,
    guardrails: dict[str, Any],
    dashboard,
    experiment_metric,
) -> list[ExperimentGuardrailBreach]:
    metric_values: dict[str, float | None] = {
        "render_success_rate": _safe_float(dashboard.summary.render_success_rate),
        "p95_latency_ms": _safe_float(dashboard.summary.p95_latency_ms),
        "avg_cost_per_render_usd": _safe_float(dashboard.summary.avg_cost_per_render_usd),
        "queue_queued_jobs": _safe_float(dashboard.queue.queued_jobs),
        "preview_to_final_rate": _safe_float(dashboard.summary.preview_to_final_rate),
        "checkout_to_paid_rate": _safe_float(dashboard.funnel.checkout_to_paid_rate),
        "paid_conversion_rate": _safe_float(experiment_metric.paid_conversion_rate if experiment_metric else None),
        "active_paid_users": _safe_float(experiment_metric.active_paid_users if experiment_metric else 0),
        "total_assigned_users": _safe_float(experiment_metric.total_assigned_users if experiment_metric else 0),
    }

    breaches: list[ExperimentGuardrailBreach] = []
    for key, raw_threshold in guardrails.items():
        if key in {"render_events_min", "total_assigned_users_min"}:
            # Sample-size gating keys are handled in _guardrail_skip_reason.
            continue

        parsed = _guardrail_rule(key)
        if not parsed:
            continue
        metric_key, operator = parsed
        threshold = _safe_float(raw_threshold)
        if threshold is None:
            continue

        actual = metric_values.get(metric_key)
        if actual is None:
            continue

        if operator == ">=" and actual < threshold:
            breaches.append(
                ExperimentGuardrailBreach(
                    metric_key=metric_key,
                    operator=operator,
                    threshold=threshold,
                    actual=actual,
                    message=f"{metric_key} is below threshold",
                )
            )
        elif operator == "<=" and actual > threshold:
            breaches.append(
                ExperimentGuardrailBreach(
                    metric_key=metric_key,
                    operator=operator,
                    threshold=threshold,
                    actual=actual,
                    message=f"{metric_key} is above threshold",
                )
            )

    return breaches


def _guardrail_rule(key: str) -> tuple[str, str] | None:
    aliases: dict[str, tuple[str, str]] = {
        "render_success_rate_min": ("render_success_rate", ">="),
        "p95_latency_max_ms": ("p95_latency_ms", "<="),
        "p95_latency_ms_max": ("p95_latency_ms", "<="),
        "avg_cost_per_render_max_usd": ("avg_cost_per_render_usd", "<="),
        "avg_cost_per_render_usd_max": ("avg_cost_per_render_usd", "<="),
        "queue_queued_jobs_max": ("queue_queued_jobs", "<="),
        "queue_backlog_max": ("queue_queued_jobs", "<="),
        "preview_to_final_rate_min": ("preview_to_final_rate", ">="),
        "checkout_to_paid_rate_min": ("checkout_to_paid_rate", ">="),
        "paid_conversion_rate_min": ("paid_conversion_rate", ">="),
        "active_paid_users_min": ("active_paid_users", ">="),
    }
    if key in aliases:
        return aliases[key]
    if "_max_" in key:
        left, right = key.split("_max_", 1)
        return (f"{left}_{right}", "<=")
    if "_min_" in key:
        left, right = key.split("_min_", 1)
        return (f"{left}_{right}", ">=")
    if key.endswith("_max"):
        return (key.removesuffix("_max"), "<=")
    if key.endswith("_min"):
        return (key.removesuffix("_min"), ">=")
    return None


def _guardrail_number(guardrails: dict[str, Any], key: str) -> float | None:
    return _safe_float(guardrails.get(key))


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_control_variant_id(*, variant_ids: list[str], configured_variant_ids: list[str]) -> str | None:
    if "control" in variant_ids:
        return "control"
    for variant_id in configured_variant_ids:
        if variant_id in variant_ids:
            return variant_id
    if variant_ids:
        return variant_ids[0]
    return None


def _primary_metric_counts(
    *,
    metric_key: str,
    assigned_users: int,
    active_paid_users: int,
    checkout_started_users: int,
    preview_users: int,
    final_users: int,
    render_events: int,
    render_success: int,
) -> tuple[float, int, int]:
    normalized = metric_key.strip().lower()

    if "render_success" in normalized:
        successes, trials = render_success, render_events
    elif "preview_to_final" in normalized:
        successes, trials = final_users, preview_users
    elif "checkout_start" in normalized:
        successes, trials = checkout_started_users, assigned_users
    elif "final_to_checkout" in normalized:
        successes, trials = checkout_started_users, final_users
    elif "checkout_to_paid" in normalized:
        successes, trials = active_paid_users, checkout_started_users
    elif "paid_conversion" in normalized or "upgrade_conversion" in normalized or "subscription" in normalized:
        successes, trials = active_paid_users, assigned_users
    else:
        # Fallback keeps legacy behavior where unknown metrics were interpreted as paid conversion.
        successes, trials = active_paid_users, assigned_users

    return (_rate(successes, trials), successes, trials)


def _lift_pct(value: float, baseline: float) -> float | None:
    if baseline == 0:
        return 0.0 if value <= 0 else None
    return round(((value - baseline) / abs(baseline)) * 100.0, 2)


def _proportion_p_value(*, success_a: int, trials_a: int, success_b: int, trials_b: int) -> float | None:
    if trials_a <= 0 or trials_b <= 0:
        return None
    pooled = (success_a + success_b) / (trials_a + trials_b)
    variance = pooled * (1.0 - pooled) * ((1.0 / trials_a) + (1.0 / trials_b))
    if variance <= 0:
        return None
    z_score = ((success_b / trials_b) - (success_a / trials_a)) / sqrt(variance)
    return erfc(abs(z_score) / sqrt(2.0))


def _recommend_variant(
    *,
    variants: list[ExperimentPerformanceVariant],
    control_variant_id: str | None,
    primary_metric: str,
    minimum_sample_size: int,
) -> tuple[str | None, str]:
    if not variants:
        return None, "No variant data is available for the selected window."
    if not control_variant_id:
        return None, "Control variant is missing; cannot compute lift-based recommendation."

    control = next((item for item in variants if item.variant_id == control_variant_id), None)
    if not control:
        return None, "Control variant has no assignment data yet."
    if control.assigned_users < minimum_sample_size:
        return (
            None,
            f"Control sample size is below minimum ({control.assigned_users} < {minimum_sample_size}).",
        )

    challengers = [
        item
        for item in variants
        if item.variant_id != control_variant_id and item.assigned_users >= minimum_sample_size
    ]
    if not challengers:
        return None, "No challenger variant reached the minimum sample size yet."

    statistically_better = [
        item for item in challengers if item.statistically_significant and (item.lift_vs_control_pct or 0.0) > 0.0
    ]
    if not statistically_better:
        best_observed = max(challengers, key=lambda item: item.primary_metric_value)
        if best_observed.primary_metric_value > control.primary_metric_value:
            return (
                None,
                f"{best_observed.variant_id} is higher on {primary_metric} but not statistically significant yet.",
            )
        return None, "Control remains best for this window."

    winner = max(
        statistically_better,
        key=lambda item: (item.primary_metric_value, item.lift_vs_control_pct or 0.0),
    )
    lift_text = "n/a" if winner.lift_vs_control_pct is None else f"{winner.lift_vs_control_pct:.2f}%"
    p_text = "n/a" if winner.p_value is None else f"{winner.p_value:.4f}"
    return (
        winner.variant_id,
        f"{winner.variant_id} beats {control_variant_id} on {primary_metric} (lift={lift_text}, p={p_text}).",
    )


def _bounded_float(value: float | None, *, default: float, min_value: float, max_value: float) -> float:
    if value is None:
        return default
    return max(min_value, min(max_value, value))


def _extract_rollout_percent(rollout_state: dict[str, Any]) -> int:
    raw = _safe_float(rollout_state.get("rollout_percent"))
    if raw is None:
        return 0
    return max(0, min(100, int(raw)))


def _next_rollout_percent(current_percent: int) -> int:
    if current_percent < 10:
        return 10
    if current_percent < 50:
        return 50
    return 100


def _new_bucket_accumulator() -> dict[str, Any]:
    return {
        "render_events": 0,
        "render_success": 0,
        "latencies": [],
        "total_cost_usd": 0.0,
        "preview_users": set(),
        "final_users": set(),
        "checkout_users": set(),
        "paid_activation_users": set(),
    }


def _build_bucket_windows(
    *,
    window_start: datetime,
    window_end: datetime,
    bucket_hours: int,
) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = window_start
    delta = timedelta(hours=max(1, int(bucket_hours)))
    while cursor < window_end:
        bucket_end = min(window_end, cursor + delta)
        windows.append((cursor, bucket_end))
        cursor = bucket_end
    return windows


def _bucket_index(
    *,
    timestamp: datetime,
    window_start: datetime,
    bucket_hours: int,
    bucket_count: int,
) -> int | None:
    if timestamp < window_start or bucket_count <= 0:
        return None
    bucket_seconds = max(1, int(bucket_hours)) * 3600
    index = int((timestamp - window_start).total_seconds() // bucket_seconds)
    if index < 0 or index >= bucket_count:
        return None
    return index


def _avg(values: list[int]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _rounded(value: float | None) -> float | None:
    return round(float(value), 2) if value is not None else None


def _percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * q))
    return float(sorted_values[index])
