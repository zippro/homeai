from __future__ import annotations

from collections import defaultdict

from sqlalchemy import desc, select

from app.db import session_scope
from app.models import AnalyticsEventModel
from app.schemas import AnalyticsEventRequest, AnalyticsOverviewResponse, JobStatus

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

    # Preserve chronological order for percentile/cost calculations.
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


def _percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * q))
    return float(sorted_values[index])
