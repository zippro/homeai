from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from app.time_utils import utc_now

from sqlalchemy import select

from app.db import session_scope
from app.models import AnalyticsEventModel


def get_provider_health(hours: int = 24) -> dict[str, dict[str, float | int]]:
    window_start = utc_now() - timedelta(hours=hours)
    with session_scope() as session:
        stmt = select(AnalyticsEventModel).where(AnalyticsEventModel.created_at >= window_start)
        rows = session.execute(stmt).scalars().all()

    provider_total: dict[str, int] = defaultdict(int)
    provider_success: dict[str, int] = defaultdict(int)
    provider_failed: dict[str, int] = defaultdict(int)
    provider_latency_sum: dict[str, int] = defaultdict(int)
    provider_latency_count: dict[str, int] = defaultdict(int)

    for row in rows:
        if not row.provider:
            continue
        if not row.event_name.startswith("render_"):
            continue

        provider = row.provider
        provider_total[provider] += 1

        if row.status == "completed":
            provider_success[provider] += 1
        elif row.status == "failed":
            provider_failed[provider] += 1

        if row.latency_ms is not None:
            provider_latency_sum[provider] += row.latency_ms
            provider_latency_count[provider] += 1

    summary: dict[str, dict[str, float | int]] = {}
    for provider, total in provider_total.items():
        success_rate = (provider_success[provider] / total) * 100.0 if total else 0.0
        avg_latency = (
            provider_latency_sum[provider] / provider_latency_count[provider]
            if provider_latency_count[provider]
            else 0.0
        )

        # Simple health formula: success is dominant, latency is secondary.
        latency_factor = 100.0 if avg_latency <= 2500 else max(0.0, 100.0 - ((avg_latency - 2500) / 75.0))
        health_score = round((success_rate * 0.7) + (latency_factor * 0.3), 2)

        summary[provider] = {
            "total_events": total,
            "success_rate": round(success_rate, 2),
            "failed_events": provider_failed[provider],
            "avg_latency_ms": round(avg_latency, 2),
            "health_score": health_score,
        }

    return summary
