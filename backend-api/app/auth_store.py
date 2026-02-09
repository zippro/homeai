from __future__ import annotations

from datetime import datetime, timedelta
from app.time_utils import utc_now
from uuid import uuid4

from sqlalchemy import select

from app.db import session_scope
from app.models import AuthSessionModel
from app.schemas import AuthMeResponse, AuthSessionResponse, DevLoginRequest, LogoutResponse


def create_dev_session(payload: DevLoginRequest) -> AuthSessionResponse:
    now = utc_now()
    expires_at = now + timedelta(hours=payload.ttl_hours)
    token = f"dev_{uuid4().hex}{uuid4().hex}"

    with session_scope() as session:
        session.add(
            AuthSessionModel(
                token=token,
                user_id=payload.user_id,
                platform=payload.platform,
                created_at=now,
                expires_at=expires_at,
                revoked_at=None,
            )
        )

    return AuthSessionResponse(
        access_token=token,
        token_type="bearer",
        user_id=payload.user_id,
        expires_at=expires_at,
    )


def get_me(token: str) -> AuthMeResponse | None:
    session_info = _get_active_session_info(token)
    if not session_info:
        return None
    user_id, platform, expires_at = session_info
    return AuthMeResponse(
        user_id=user_id,
        platform=platform,
        expires_at=expires_at,
    )


def revoke_session(token: str) -> LogoutResponse:
    with session_scope() as session:
        model = session.get(AuthSessionModel, token)
        if not model:
            return LogoutResponse(revoked=False)
        if model.revoked_at is not None:
            return LogoutResponse(revoked=False)
        model.revoked_at = utc_now()
        return LogoutResponse(revoked=True)


def resolve_authenticated_user(token: str) -> str | None:
    session_info = _get_active_session_info(token)
    if not session_info:
        return None
    user_id, _, _ = session_info
    return user_id


def _get_active_session_info(token: str) -> tuple[str, str | None, datetime] | None:
    now = utc_now()
    with session_scope() as session:
        stmt = select(AuthSessionModel).where(AuthSessionModel.token == token)
        model = session.execute(stmt).scalar_one_or_none()
        if not model:
            return None
        if model.revoked_at is not None:
            return None
        if model.expires_at <= now:
            return None
        return model.user_id, model.platform, model.expires_at
