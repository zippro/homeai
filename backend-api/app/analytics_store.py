from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from app.time_utils import utc_now

from sqlalchemy import desc, func, select

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
from app.product_store import get_variable_map
from app.schemas import (
    AnalyticsAlert,
    AnalyticsCreditsMetrics,
    AnalyticsCreditReasonMetric,
    AnalyticsDashboardResponse,
    AnalyticsDashboardSummary,
    AnalyticsEventRequest,
    AnalyticsExperimentMetric,
    AnalyticsExperimentVariantMetric,
    AnalyticsFunnelMetrics,
    AnalyticsOperationMetric,
    AnalyticsOverviewResponse,
    AnalyticsPlatformMetric,
    AnalyticsProviderMetric,
    AnalyticsQueueMetrics,
    AnalyticsStatusMetric,
    AnalyticsSubscriptionSourceMetric,
    AnalyticsSubscriptionMetrics,
    JobStatus,
    RenderTier,
)

_MAX_EVENTS_SCAN = 20000


def ingest_event(event: AnalyticsEventRequest) -> None:
    with session_scope() as session:
        session.add(
            AnalyticsEventModel(
                event_name=event.event_name,
                user_id=event.user_id,
                platform=event.platform,
                provider=event.provider,
                operation=event.operation.value if event.operation else None,
                status=event.status.value if event.status else None,
                latency_ms=event.latency_ms,
                cost_usd=event.cost_usd,
                occurred_at=event.occurred_at,
            )
        )


def get_analytics_overview() -> AnalyticsOverviewResponse:
    with session_scope() as session:
        stmt = select(AnalyticsEventModel).order_by(desc(AnalyticsEventModel.id)).limit(_MAX_EVENTS_SCAN)
        rows = session.execute(stmt).scalars().all()

    snapshot = list(reversed(rows))
    render_events = [row for row in snapshot if row.event_name.startswith("render_")]

    render_success = sum(1 for row in render_events if row.status == JobStatus.completed.value)
    render_failed = sum(1 for row in render_events if row.status == JobStatus.failed.value)

    latencies = [row.latency_ms for row in render_events if row.latency_ms is not None]
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    p95_latency = _percentile(latencies, 0.95) if latencies else None

    provider_counts: dict[str, int] = defaultdict(int)
    provider_success_total: dict[str, int] = defaultdict(int)
    provider_event_total: dict[str, int] = defaultdict(int)

    for row in render_events:
        if row.provider:
            provider_counts[row.provider] += 1
            provider_event_total[row.provider] += 1
            if row.status == JobStatus.completed.value:
                provider_success_total[row.provider] += 1

    provider_success_rate = {
        provider: round((provider_success_total[provider] / total) * 100.0, 2)
        for provider, total in provider_event_total.items()
        if total > 0
    }

    total_cost = round(sum(float(row.cost_usd) for row in snapshot if row.cost_usd is not None), 6)

    return AnalyticsOverviewResponse(
        total_events=len(snapshot),
        render_events=len(render_events),
        render_success=render_success,
        render_failed=render_failed,
        render_success_rate=round((render_success / len(render_events)) * 100.0, 2) if render_events else 0.0,
        avg_latency_ms=round(avg_latency, 2) if avg_latency is not None else None,
        p95_latency_ms=round(p95_latency, 2) if p95_latency is not None else None,
        total_cost_usd=total_cost,
        provider_event_counts=dict(provider_counts),
        provider_success_rate=provider_success_rate,
    )


def get_analytics_dashboard(hours: int = 24) -> AnalyticsDashboardResponse:
    now = utc_now()
    window_hours = max(1, int(hours))
    window_start = now - timedelta(hours=window_hours)

    with session_scope() as session:
        event_stmt = (
            select(AnalyticsEventModel)
            .where(AnalyticsEventModel.occurred_at >= window_start)
            .order_by(AnalyticsEventModel.id)
        )
        events = session.execute(event_stmt).scalars().all()

        ledger_stmt = select(CreditLedgerEntryModel).where(CreditLedgerEntryModel.created_at >= window_start)
        ledger_rows = session.execute(ledger_stmt).scalars().all()

        active_sub_stmt = select(SubscriptionEntitlementModel).where(
            SubscriptionEntitlementModel.status == "active"
        )
        active_subscriptions = session.execute(active_sub_stmt).scalars().all()

        experiment_stmt = select(ExperimentModel).order_by(desc(ExperimentModel.updated_at)).limit(200)
        experiments = session.execute(experiment_stmt).scalars().all()

        experiment_ids = [item.experiment_id for item in experiments]
        if experiment_ids:
            assignment_stmt = select(ExperimentAssignmentModel).where(
                ExperimentAssignmentModel.experiment_id.in_(experiment_ids)
            )
            experiment_assignments = session.execute(assignment_stmt).scalars().all()
        else:
            experiment_assignments = []

        login_users = int(
            session.execute(
                select(func.count(func.distinct(AuthSessionModel.user_id))).where(
                    AuthSessionModel.created_at >= window_start
                )
            ).scalar_one()
            or 0
        )

        queued_jobs = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(RenderJobModel.status == JobStatus.queued.value)
            ).scalar_one()
            or 0
        )
        in_progress_jobs = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(RenderJobModel.status == JobStatus.in_progress.value)
            ).scalar_one()
            or 0
        )
        completed_jobs_window = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(
                    RenderJobModel.status == JobStatus.completed.value,
                    RenderJobModel.updated_at >= window_start,
                )
            ).scalar_one()
            or 0
        )
        failed_jobs_window = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(
                    RenderJobModel.status == JobStatus.failed.value,
                    RenderJobModel.updated_at >= window_start,
                )
            ).scalar_one()
            or 0
        )
        canceled_jobs_window = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(
                    RenderJobModel.status == JobStatus.canceled.value,
                    RenderJobModel.updated_at >= window_start,
                )
            ).scalar_one()
            or 0
        )
        preview_completed = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(
                    RenderJobModel.tier == RenderTier.preview.value,
                    RenderJobModel.status == JobStatus.completed.value,
                    RenderJobModel.updated_at >= window_start,
                )
            ).scalar_one()
            or 0
        )
        final_completed = int(
            session.execute(
                select(func.count())
                .select_from(RenderJobModel)
                .where(
                    RenderJobModel.tier == RenderTier.final.value,
                    RenderJobModel.status == JobStatus.completed.value,
                    RenderJobModel.updated_at >= window_start,
                )
            ).scalar_one()
            or 0
        )

    render_events = [row for row in events if row.event_name.startswith("render_")]

    unique_users = len({row.user_id for row in events if row.user_id})
    active_render_users = len({row.user_id for row in render_events if row.user_id})

    status_counter = Counter((row.status or "unknown") for row in render_events)
    render_success = int(status_counter.get(JobStatus.completed.value, 0))
    render_failed = int(status_counter.get(JobStatus.failed.value, 0))
    render_in_progress = int(
        status_counter.get(JobStatus.queued.value, 0) + status_counter.get(JobStatus.in_progress.value, 0)
    )

    latencies = [row.latency_ms for row in render_events if row.latency_ms is not None]
    avg_latency = _avg(latencies)
    p50_latency = _percentile(latencies, 0.50) if latencies else None
    p95_latency = _percentile(latencies, 0.95) if latencies else None

    total_cost = round(sum(float(row.cost_usd) for row in render_events if row.cost_usd is not None), 6)
    avg_cost_per_render = (total_cost / len(render_events)) if render_events else None

    summary = AnalyticsDashboardSummary(
        window_hours=window_hours,
        total_events=len(events),
        unique_users=unique_users,
        active_render_users=active_render_users,
        render_events=len(render_events),
        render_success=render_success,
        render_failed=render_failed,
        render_in_progress=render_in_progress,
        render_success_rate=_rate(render_success, len(render_events)),
        preview_completed=preview_completed,
        final_completed=final_completed,
        preview_to_final_rate=_rate(final_completed, preview_completed),
        avg_latency_ms=_rounded(avg_latency),
        p50_latency_ms=_rounded(p50_latency),
        p95_latency_ms=_rounded(p95_latency),
        total_cost_usd=round(total_cost, 6),
        avg_cost_per_render_usd=_rounded(avg_cost_per_render),
    )

    provider_breakdown = _build_provider_breakdown(render_events)
    operation_breakdown = _build_operation_breakdown(render_events)
    platform_breakdown = _build_platform_breakdown(events, render_events)
    status_breakdown = _build_status_breakdown(status_counter)

    credits_metrics = _build_credits_metrics(ledger_rows)
    subscription_metrics = _build_subscription_metrics(active_subscriptions, now)
    subscription_source_metrics = _build_subscription_source_metrics(active_subscriptions)

    preview_users = len(
        {
            row.user_id
            for row in ledger_rows
            if row.delta < 0 and row.reason == "render_preview" and row.user_id
        }
    )
    final_users = len(
        {
            row.user_id
            for row in ledger_rows
            if row.delta < 0 and row.reason == "render_final" and row.user_id
        }
    )
    checkout_events = {"checkout_started", "web_checkout_started", "checkout_session_started"}
    checkout_starts = sum(1 for row in events if row.event_name in checkout_events)
    paid_activations = sum(1 for row in active_subscriptions if row.updated_at >= window_start)

    funnel_metrics = AnalyticsFunnelMetrics(
        login_users=login_users,
        preview_users=preview_users,
        final_users=final_users,
        checkout_starts=checkout_starts,
        paid_activations=paid_activations,
        login_to_preview_rate=_rate(preview_users, login_users),
        preview_to_final_rate=_rate(final_users, preview_users),
        final_to_checkout_rate=_rate(checkout_starts, final_users),
        checkout_to_paid_rate=_rate(paid_activations, checkout_starts),
    )

    active_paid_user_ids = {row.user_id for row in active_subscriptions}
    experiment_breakdown = _build_experiment_breakdown(
        experiments=experiments,
        assignments=experiment_assignments,
        active_paid_user_ids=active_paid_user_ids,
    )

    queue_metrics = AnalyticsQueueMetrics(
        queued_jobs=queued_jobs,
        in_progress_jobs=in_progress_jobs,
        completed_jobs_window=completed_jobs_window,
        failed_jobs_window=failed_jobs_window,
        canceled_jobs_window=canceled_jobs_window,
    )

    alerts = _build_alerts(
        summary=summary,
        queue_metrics=queue_metrics,
        provider_breakdown=provider_breakdown,
    )

    return AnalyticsDashboardResponse(
        generated_at=now,
        summary=summary,
        provider_breakdown=provider_breakdown,
        operation_breakdown=operation_breakdown,
        platform_breakdown=platform_breakdown,
        status_breakdown=status_breakdown,
        credits=credits_metrics,
        subscriptions=subscription_metrics,
        subscription_sources=subscription_source_metrics,
        queue=queue_metrics,
        funnel=funnel_metrics,
        experiment_breakdown=experiment_breakdown,
        alerts=alerts,
    )


def _build_provider_breakdown(render_events: list[AnalyticsEventModel]) -> list[AnalyticsProviderMetric]:
    grouped: dict[str, list[AnalyticsEventModel]] = defaultdict(list)
    for row in render_events:
        grouped[row.provider or "unknown"].append(row)

    rows: list[AnalyticsProviderMetric] = []
    for provider, provider_rows in grouped.items():
        success = sum(1 for row in provider_rows if row.status == JobStatus.completed.value)
        latencies = [row.latency_ms for row in provider_rows if row.latency_ms is not None]
        total_cost = sum(float(row.cost_usd) for row in provider_rows if row.cost_usd is not None)
        rows.append(
            AnalyticsProviderMetric(
                provider=provider,
                total_events=len(provider_rows),
                success_rate=_rate(success, len(provider_rows)),
                avg_latency_ms=_rounded(_avg(latencies)),
                p95_latency_ms=_rounded(_percentile(latencies, 0.95) if latencies else None),
                total_cost_usd=round(total_cost, 6),
                avg_cost_usd=_rounded(total_cost / len(provider_rows) if provider_rows else None),
            )
        )
    rows.sort(key=lambda item: item.total_events, reverse=True)
    return rows


def _build_operation_breakdown(render_events: list[AnalyticsEventModel]) -> list[AnalyticsOperationMetric]:
    grouped: dict[str, list[AnalyticsEventModel]] = defaultdict(list)
    for row in render_events:
        grouped[row.operation or "unknown"].append(row)

    rows: list[AnalyticsOperationMetric] = []
    for operation, operation_rows in grouped.items():
        success = sum(1 for row in operation_rows if row.status == JobStatus.completed.value)
        latencies = [row.latency_ms for row in operation_rows if row.latency_ms is not None]
        total_cost = sum(float(row.cost_usd) for row in operation_rows if row.cost_usd is not None)
        rows.append(
            AnalyticsOperationMetric(
                operation=operation,
                total_events=len(operation_rows),
                success_rate=_rate(success, len(operation_rows)),
                avg_latency_ms=_rounded(_avg(latencies)),
                p95_latency_ms=_rounded(_percentile(latencies, 0.95) if latencies else None),
                total_cost_usd=round(total_cost, 6),
                avg_cost_usd=_rounded(total_cost / len(operation_rows) if operation_rows else None),
            )
        )
    rows.sort(key=lambda item: item.total_events, reverse=True)
    return rows


def _build_platform_breakdown(
    events: list[AnalyticsEventModel],
    render_events: list[AnalyticsEventModel],
) -> list[AnalyticsPlatformMetric]:
    grouped_total: dict[str, int] = defaultdict(int)
    grouped_render: dict[str, int] = defaultdict(int)
    grouped_success: dict[str, int] = defaultdict(int)

    for row in events:
        grouped_total[row.platform or "unknown"] += 1

    for row in render_events:
        platform = row.platform or "unknown"
        grouped_render[platform] += 1
        if row.status == JobStatus.completed.value:
            grouped_success[platform] += 1

    platforms = set(grouped_total.keys()) | set(grouped_render.keys())
    rows = [
        AnalyticsPlatformMetric(
            platform=platform,
            total_events=grouped_total[platform],
            render_events=grouped_render[platform],
            render_success=grouped_success[platform],
            render_success_rate=_rate(grouped_success[platform], grouped_render[platform]),
        )
        for platform in platforms
    ]
    rows.sort(key=lambda item: item.total_events, reverse=True)
    return rows


def _build_status_breakdown(status_counter: Counter[str]) -> list[AnalyticsStatusMetric]:
    rows = [AnalyticsStatusMetric(status=status, count=int(count)) for status, count in status_counter.items()]
    rows.sort(key=lambda item: item.count, reverse=True)
    return rows


def _build_credits_metrics(ledger_rows: list[CreditLedgerEntryModel]) -> AnalyticsCreditsMetrics:
    consumed_total = sum(-row.delta for row in ledger_rows if row.delta < 0)
    granted_total = sum(row.delta for row in ledger_rows if row.delta > 0)
    refunded_total = sum(
        row.delta
        for row in ledger_rows
        if row.delta > 0 and row.reason.startswith("render_refund")
    )
    daily_reset_total = sum(row.delta for row in ledger_rows if row.delta > 0 and row.reason == "daily_reset")
    unique_consumers = len({row.user_id for row in ledger_rows if row.delta < 0})

    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"events": 0, "net_delta": 0, "absolute_delta": 0})
    for row in ledger_rows:
        entry = grouped[row.reason]
        entry["events"] += 1
        entry["net_delta"] += int(row.delta)
        entry["absolute_delta"] += abs(int(row.delta))

    top_reasons = [
        AnalyticsCreditReasonMetric(
            reason=reason,
            events=stats["events"],
            net_delta=stats["net_delta"],
            absolute_delta=stats["absolute_delta"],
        )
        for reason, stats in grouped.items()
    ]
    top_reasons.sort(key=lambda item: (item.absolute_delta, item.events), reverse=True)

    return AnalyticsCreditsMetrics(
        consumed_total=int(consumed_total),
        granted_total=int(granted_total),
        refunded_total=int(refunded_total),
        daily_reset_total=int(daily_reset_total),
        unique_consumers=unique_consumers,
        top_reasons=top_reasons[:8],
    )


def _build_subscription_metrics(
    active_subscriptions: list[SubscriptionEntitlementModel],
    now: datetime,
) -> AnalyticsSubscriptionMetrics:
    plan_counter: dict[str, int] = defaultdict(int)
    renewals_due_7d = 0
    expirations_due_7d = 0
    in_7_days = now + timedelta(days=7)

    for row in active_subscriptions:
        plan_counter[row.plan_id] += 1
        if row.renews_at and now <= row.renews_at <= in_7_days:
            renewals_due_7d += 1
        if row.expires_at and now <= row.expires_at <= in_7_days:
            expirations_due_7d += 1

    return AnalyticsSubscriptionMetrics(
        active_subscriptions=len(active_subscriptions),
        active_by_plan=dict(sorted(plan_counter.items())),
        renewals_due_7d=renewals_due_7d,
        expirations_due_7d=expirations_due_7d,
    )


def _build_subscription_source_metrics(
    active_subscriptions: list[SubscriptionEntitlementModel],
) -> list[AnalyticsSubscriptionSourceMetric]:
    source_counter: dict[str, int] = defaultdict(int)
    for row in active_subscriptions:
        source_counter[row.source or "unknown"] += 1

    total_active = len(active_subscriptions)
    rows = [
        AnalyticsSubscriptionSourceMetric(
            source=source,
            active_subscriptions=count,
            active_share_pct=_rate(count, total_active),
        )
        for source, count in source_counter.items()
    ]
    rows.sort(key=lambda item: item.active_subscriptions, reverse=True)
    return rows


def _build_experiment_breakdown(
    *,
    experiments: list[ExperimentModel],
    assignments: list[ExperimentAssignmentModel],
    active_paid_user_ids: set[str],
) -> list[AnalyticsExperimentMetric]:
    assignments_by_experiment: dict[str, list[ExperimentAssignmentModel]] = defaultdict(list)
    for row in assignments:
        assignments_by_experiment[row.experiment_id].append(row)

    rows: list[AnalyticsExperimentMetric] = []
    for experiment in experiments:
        payload = dict(experiment.payload_json or {})
        name = str(payload.get("name") or experiment.experiment_id)
        primary_metric = str(payload.get("primary_metric") or "paid_conversion")
        variants_payload = payload.get("variants") or []
        configured_variant_ids = [
            str(item.get("variant_id"))
            for item in variants_payload
            if str(item.get("variant_id") or "").strip()
        ]

        experiment_assignments = assignments_by_experiment.get(experiment.experiment_id, [])
        users_by_variant: dict[str, set[str]] = defaultdict(set)
        for assignment in experiment_assignments:
            users_by_variant[assignment.variant_id].add(assignment.user_id)

        variant_ids = list(dict.fromkeys(configured_variant_ids + sorted(users_by_variant.keys())))
        variant_rows: list[AnalyticsExperimentVariantMetric] = []
        assigned_users_all: set[str] = set()
        for variant_id in variant_ids:
            assigned_users = users_by_variant.get(variant_id, set())
            active_paid_users = assigned_users & active_paid_user_ids
            assigned_users_all.update(assigned_users)
            variant_rows.append(
                AnalyticsExperimentVariantMetric(
                    variant_id=variant_id,
                    assigned_users=len(assigned_users),
                    active_paid_users=len(active_paid_users),
                    paid_conversion_rate=_rate(len(active_paid_users), len(assigned_users)),
                )
            )

        total_assigned_users = len(assigned_users_all)
        total_active_paid_users = len(assigned_users_all & active_paid_user_ids)
        rows.append(
            AnalyticsExperimentMetric(
                experiment_id=experiment.experiment_id,
                name=name,
                primary_metric=primary_metric,
                is_active=bool(experiment.is_active),
                total_assigned_users=total_assigned_users,
                active_paid_users=total_active_paid_users,
                paid_conversion_rate=_rate(total_active_paid_users, total_assigned_users),
                variants=variant_rows,
            )
        )

    rows.sort(key=lambda item: item.total_assigned_users, reverse=True)
    return rows


def _build_alerts(
    *,
    summary: AnalyticsDashboardSummary,
    queue_metrics: AnalyticsQueueMetrics,
    provider_breakdown: list[AnalyticsProviderMetric],
) -> list[AnalyticsAlert]:
    variables = get_variable_map()

    min_success_rate = _as_float(variables.get("analytics_alert_min_success_rate_pct"), 85.0)
    max_p95_latency = _as_float(variables.get("analytics_alert_max_p95_latency_ms"), 12000.0)
    max_avg_cost = _as_float(variables.get("analytics_alert_max_avg_cost_usd"), 0.12)
    max_queued_jobs = _as_float(variables.get("analytics_alert_max_queued_jobs"), 50.0)

    alerts: list[AnalyticsAlert] = []

    if summary.render_events >= 20 and summary.render_success_rate < min_success_rate:
        alerts.append(
            AnalyticsAlert(
                code="render_success_rate_low",
                severity="critical",
                message="Render success rate is below the configured threshold.",
                current_value=summary.render_success_rate,
                threshold=min_success_rate,
            )
        )

    if summary.p95_latency_ms is not None and summary.render_events >= 10 and summary.p95_latency_ms > max_p95_latency:
        alerts.append(
            AnalyticsAlert(
                code="render_latency_high",
                severity="warning",
                message="P95 render latency is above the configured threshold.",
                current_value=summary.p95_latency_ms,
                threshold=max_p95_latency,
            )
        )

    if (
        summary.avg_cost_per_render_usd is not None
        and summary.render_events >= 10
        and summary.avg_cost_per_render_usd > max_avg_cost
    ):
        alerts.append(
            AnalyticsAlert(
                code="render_cost_high",
                severity="warning",
                message="Average cost per render is above the configured threshold.",
                current_value=summary.avg_cost_per_render_usd,
                threshold=max_avg_cost,
            )
        )

    if queue_metrics.queued_jobs > max_queued_jobs:
        alerts.append(
            AnalyticsAlert(
                code="queue_backlog_high",
                severity="warning",
                message="Queued render jobs exceed the configured threshold.",
                current_value=queue_metrics.queued_jobs,
                threshold=max_queued_jobs,
            )
        )

    weak_providers = [
        row.provider
        for row in provider_breakdown
        if row.total_events >= 10 and row.success_rate < min_success_rate
    ]
    if weak_providers:
        alerts.append(
            AnalyticsAlert(
                code="provider_success_low",
                severity="warning",
                message=f"Providers below success threshold: {', '.join(weak_providers)}",
                current_value=len(weak_providers),
                threshold=0,
            )
        )

    return alerts


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


def _as_float(value: object, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * q))
    return float(sorted_values[index])
