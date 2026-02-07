from __future__ import annotations

from fastapi import APIRouter, Query

from app.discover_store import get_discover_feed
from app.schemas import DiscoverFeedResponse

router = APIRouter(prefix="/v1/discover", tags=["discover"])


@router.get("/feed", response_model=DiscoverFeedResponse)
async def discover_feed(tab: str | None = Query(default=None)) -> DiscoverFeedResponse:
    return get_discover_feed(tab=tab)
