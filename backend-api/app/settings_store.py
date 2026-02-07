from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select

from app.db import session_scope
from app.models import AdminAuditLogModel, ProviderSettingsStateModel, ProviderSettingsVersionModel
from app.schemas import (
    AdminActionRequest,
    AuditLogEntry,
    ProviderSettings,
    ProviderSettingsUpdateRequest,
    ProviderSettingsVersionSummary,
)

_PROVIDER_DOMAIN = "provider_settings"
_STATE_ID = 1


def bootstrap_provider_settings() -> None:
    with session_scope() as session:
        state = session.get(ProviderSettingsStateModel, _STATE_ID)
        if state:
            return

        initial = ProviderSettings()
        initial_json = initial.model_dump(mode="json")

        state = ProviderSettingsStateModel(
            id=_STATE_ID,
            current_version=1,
            published_json=initial_json,
            draft_json=initial_json,
        )
        session.add(state)
        session.add(
            ProviderSettingsVersionModel(
                version=1,
                actor="system",
                reason="initial_bootstrap",
                source_version=None,
                settings_json=initial_json,
                created_at=datetime.utcnow(),
            )
        )


def get_provider_settings() -> ProviderSettings:
    with session_scope() as session:
        state = _get_or_create_state(session)
        return ProviderSettings.model_validate(state.published_json)


def get_provider_settings_draft() -> ProviderSettings:
    with session_scope() as session:
        state = _get_or_create_state(session)
        return ProviderSettings.model_validate(state.draft_json)


def get_provider_settings_meta() -> dict[str, int]:
    with session_scope() as session:
        state = _get_or_create_state(session)
        return {"current_version": state.current_version}


def update_provider_settings(
    payload: ProviderSettingsUpdateRequest,
    available_providers: set[str],
) -> ProviderSettings:
    action = AdminActionRequest(actor="legacy_put", reason="Immediate publish from PUT /provider-settings")
    update_provider_settings_draft(payload, available_providers, action)
    publish_provider_settings(available_providers, action)
    return get_provider_settings()


def update_provider_settings_draft(
    payload: ProviderSettingsUpdateRequest,
    available_providers: set[str],
    action: AdminActionRequest,
) -> ProviderSettings:
    with session_scope() as session:
        state = _get_or_create_state(session)
        draft_settings = ProviderSettings.model_validate(state.draft_json)
        updated = draft_settings.model_copy(update=payload.model_dump(exclude_none=True), deep=True)

        _validate_settings(updated, available_providers)
        state.draft_json = updated.model_dump(mode="json")
        state.updated_at = datetime.utcnow()

        _append_audit(
            session=session,
            entry=AuditLogEntry(
                action="provider_settings_draft_updated",
                actor=action.actor,
                reason=action.reason,
                metadata={"pending_version": state.current_version + 1},
            ),
        )

        return updated


def publish_provider_settings(
    available_providers: set[str],
    action: AdminActionRequest,
) -> ProviderSettingsVersionSummary:
    with session_scope() as session:
        state = _get_or_create_state(session)
        draft_settings = ProviderSettings.model_validate(state.draft_json)
        _validate_settings(draft_settings, available_providers)

        source_version = state.current_version
        new_version = source_version + 1
        payload_json = draft_settings.model_dump(mode="json")

        state.published_json = payload_json
        state.current_version = new_version
        state.updated_at = datetime.utcnow()

        session.add(
            ProviderSettingsVersionModel(
                version=new_version,
                actor=action.actor,
                reason=action.reason,
                source_version=source_version,
                settings_json=payload_json,
                created_at=datetime.utcnow(),
            )
        )

        _append_audit(
            session=session,
            entry=AuditLogEntry(
                action="provider_settings_published",
                actor=action.actor,
                reason=action.reason,
                metadata={"version": new_version},
            ),
        )

        return ProviderSettingsVersionSummary(
            version=new_version,
            actor=action.actor,
            reason=action.reason,
            created_at=datetime.utcnow(),
        )


def rollback_provider_settings(
    version: int,
    available_providers: set[str],
    action: AdminActionRequest,
) -> ProviderSettingsVersionSummary:
    with session_scope() as session:
        state = _get_or_create_state(session)
        target = session.get(ProviderSettingsVersionModel, version)
        if not target:
            raise ValueError(f"Unknown provider settings version: {version}")

        settings = ProviderSettings.model_validate(target.settings_json)
        _validate_settings(settings, available_providers)

        source_version = state.current_version
        new_version = source_version + 1
        payload_json = settings.model_dump(mode="json")

        state.published_json = payload_json
        state.draft_json = payload_json
        state.current_version = new_version
        state.updated_at = datetime.utcnow()

        session.add(
            ProviderSettingsVersionModel(
                version=new_version,
                actor=action.actor,
                reason=action.reason or f"rollback_from_{version}",
                source_version=version,
                settings_json=payload_json,
                created_at=datetime.utcnow(),
            )
        )

        _append_audit(
            session=session,
            entry=AuditLogEntry(
                action="provider_settings_rolled_back",
                actor=action.actor,
                reason=action.reason,
                metadata={"version": new_version, "source_version": version},
            ),
        )

        return ProviderSettingsVersionSummary(
            version=new_version,
            actor=action.actor,
            reason=action.reason or f"rollback_from_{version}",
            created_at=datetime.utcnow(),
        )


def list_provider_settings_versions(limit: int = 50) -> list[ProviderSettingsVersionSummary]:
    with session_scope() as session:
        stmt = select(ProviderSettingsVersionModel).order_by(desc(ProviderSettingsVersionModel.version)).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [
            ProviderSettingsVersionSummary(
                version=row.version,
                actor=row.actor,
                reason=row.reason,
                created_at=row.created_at,
            )
            for row in rows
        ]


def list_provider_settings_audit(limit: int = 100) -> list[AuditLogEntry]:
    with session_scope() as session:
        stmt = (
            select(AdminAuditLogModel)
            .where(AdminAuditLogModel.domain == _PROVIDER_DOMAIN)
            .order_by(desc(AdminAuditLogModel.created_at))
            .limit(limit)
        )
        rows = session.execute(stmt).scalars().all()
        return [_audit_model_to_schema(row) for row in rows]


def _get_or_create_state(session) -> ProviderSettingsStateModel:
    state = session.get(ProviderSettingsStateModel, _STATE_ID)
    if state:
        return state

    initial = ProviderSettings()
    initial_json = initial.model_dump(mode="json")

    state = ProviderSettingsStateModel(
        id=_STATE_ID,
        current_version=1,
        published_json=initial_json,
        draft_json=initial_json,
    )
    session.add(state)

    existing_version = session.get(ProviderSettingsVersionModel, 1)
    if not existing_version:
        session.add(
            ProviderSettingsVersionModel(
                version=1,
                actor="system",
                reason="autocreated_state",
                source_version=None,
                settings_json=initial_json,
                created_at=datetime.utcnow(),
            )
        )
    return state


def _append_audit(session, entry: AuditLogEntry) -> None:
    session.add(
        AdminAuditLogModel(
            id=entry.id,
            domain=_PROVIDER_DOMAIN,
            action=entry.action,
            actor=entry.actor,
            reason=entry.reason,
            metadata_json=entry.metadata,
            created_at=entry.created_at,
        )
    )


def _audit_model_to_schema(model: AdminAuditLogModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=model.id,
        action=model.action,
        actor=model.actor,
        reason=model.reason,
        created_at=model.created_at,
        metadata=model.metadata_json or {},
    )


def _validate_settings(settings: ProviderSettings, available_providers: set[str]) -> None:
    if not settings.enabled_providers:
        raise ValueError("At least one provider must be enabled")

    unknown_enabled = set(settings.enabled_providers) - available_providers
    if unknown_enabled:
        raise ValueError(f"Enabled providers not registered: {sorted(unknown_enabled)}")

    if settings.default_provider not in settings.enabled_providers:
        raise ValueError("default_provider must be present in enabled_providers")

    unknown_fallback = set(settings.fallback_chain) - set(settings.enabled_providers)
    if unknown_fallback:
        raise ValueError(f"fallback_chain contains disabled providers: {sorted(unknown_fallback)}")

    for provider_name in settings.enabled_providers:
        if provider_name not in settings.provider_models:
            raise ValueError(f"Missing provider model mapping for enabled provider: {provider_name}")
