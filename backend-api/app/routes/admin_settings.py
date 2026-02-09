from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_admin_access
from app.providers.registry import get_provider_registry
from app.schemas import (
    AdminActionRequest,
    AuditLogEntry,
    ProviderSettings,
    ProviderSettingsUpdateRequest,
    ProviderSettingsVersionSummary,
)
from app.settings_store import (
    get_provider_settings,
    get_provider_settings_draft,
    list_provider_settings_audit,
    list_provider_settings_versions,
    publish_provider_settings,
    rollback_provider_settings,
    update_provider_settings,
    update_provider_settings_draft,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin_access)])


@router.get("/provider-settings", response_model=ProviderSettings)
async def get_settings() -> ProviderSettings:
    return get_provider_settings()


@router.get("/provider-settings/draft", response_model=ProviderSettings)
async def get_settings_draft() -> ProviderSettings:
    return get_provider_settings_draft()


@router.put("/provider-settings", response_model=ProviderSettings)
async def put_settings(payload: ProviderSettingsUpdateRequest) -> ProviderSettings:
    registry = get_provider_registry()
    try:
        return update_provider_settings(payload, set(registry.keys()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/provider-settings/draft", response_model=ProviderSettings)
async def put_settings_draft(
    payload: ProviderSettingsUpdateRequest,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> ProviderSettings:
    registry = get_provider_registry()
    try:
        return update_provider_settings_draft(
            payload=payload,
            available_providers=set(registry.keys()),
            action=AdminActionRequest(actor=actor, reason=reason),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/provider-settings/publish", response_model=ProviderSettingsVersionSummary)
async def publish_settings(payload: AdminActionRequest) -> ProviderSettingsVersionSummary:
    registry = get_provider_registry()
    try:
        return publish_provider_settings(available_providers=set(registry.keys()), action=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/provider-settings/rollback/{version}", response_model=ProviderSettingsVersionSummary)
async def rollback_settings(version: int, payload: AdminActionRequest) -> ProviderSettingsVersionSummary:
    registry = get_provider_registry()
    try:
        return rollback_provider_settings(
            version=version,
            available_providers=set(registry.keys()),
            action=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/provider-settings/versions", response_model=list[ProviderSettingsVersionSummary])
async def list_settings_versions(limit: int = Query(default=50, ge=1, le=500)) -> list[ProviderSettingsVersionSummary]:
    return list_provider_settings_versions(limit=limit)


@router.get("/provider-settings/audit", response_model=list[AuditLogEntry])
async def list_settings_audit(limit: int = Query(default=100, ge=1, le=1000)) -> list[AuditLogEntry]:
    return list_provider_settings_audit(limit=limit)
