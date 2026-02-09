from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import require_admin_access
from app.analytics_store import get_analytics_dashboard, get_analytics_overview, ingest_event
from app.schemas import (
    AnalyticsDashboardResponse,
    AnalyticsEventRequest,
    AnalyticsOverviewResponse,
    EventIngestResponse,
)

router = APIRouter(prefix="/v1", tags=["analytics"])


@router.post("/analytics/events", response_model=EventIngestResponse)
async def post_event(payload: AnalyticsEventRequest) -> EventIngestResponse:
    ingest_event(payload)
    return EventIngestResponse(accepted=True)


@router.get("/admin/analytics/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(_: str = Depends(require_admin_access)) -> AnalyticsOverviewResponse:
    return get_analytics_overview()


@router.get("/admin/analytics/dashboard", response_model=AnalyticsDashboardResponse)
async def analytics_dashboard(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    _: str = Depends(require_admin_access),
) -> AnalyticsDashboardResponse:
    return get_analytics_dashboard(hours=hours)
