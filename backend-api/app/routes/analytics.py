from __future__ import annotations

from fastapi import APIRouter

from app.analytics_store import get_analytics_overview, ingest_event
from app.schemas import AnalyticsEventRequest, AnalyticsOverviewResponse, EventIngestResponse

router = APIRouter(prefix="/v1", tags=["analytics"])


@router.post("/analytics/events", response_model=EventIngestResponse)
async def post_event(payload: AnalyticsEventRequest) -> EventIngestResponse:
    ingest_event(payload)
    return EventIngestResponse(accepted=True)


@router.get("/admin/analytics/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview() -> AnalyticsOverviewResponse:
    return get_analytics_overview()
