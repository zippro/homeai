from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import require_admin_access
from app.provider_health_store import get_provider_health

router = APIRouter(prefix="/v1/admin", tags=["admin", "health"], dependencies=[Depends(require_admin_access)])


@router.get("/providers/health", response_model=dict[str, dict[str, float | int]])
async def provider_health(hours: int = Query(default=24, ge=1, le=168)) -> dict[str, dict[str, float | int]]:
    return get_provider_health(hours=hours)
