from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status

from app.auth_store import resolve_authenticated_user
from app.auth_utils import parse_bearer_token
from app.runtime_env import is_production_mode, read_bool_env


def get_authenticated_user(authorization: str | None = Header(default=None)) -> str:
    return _resolve_authenticated_user_or_raise(authorization)


def get_optional_authenticated_user(authorization: str | None = Header(default=None)) -> str | None:
    token = parse_bearer_token(authorization)
    if not token:
        return None
    user_id = resolve_authenticated_user(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_expired_token")
    return user_id


def require_admin_access(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> str:
    configured_token = os.getenv("ADMIN_API_TOKEN", "").strip()
    configured_admin_users = _parse_admin_users_env(os.getenv("ADMIN_USER_IDS", ""))

    if not configured_token and not configured_admin_users:
        allow_open_mode_default = not is_production_mode()
        allow_open_mode = read_bool_env("ALLOW_OPEN_ADMIN_MODE", allow_open_mode_default)
        if allow_open_mode:
            return "open_admin_mode"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_auth_not_configured")

    if configured_token and x_admin_token:
        if secrets.compare_digest(x_admin_token, configured_token):
            return "admin_api_token"

    if configured_admin_users:
        user_id = _resolve_authenticated_user_or_raise(authorization)
        if user_id in configured_admin_users:
            return user_id
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_admin_scope")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_or_invalid_admin_token")


def assert_same_user(authenticated_user_id: str, requested_user_id: str) -> None:
    if authenticated_user_id != requested_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_scope")


def _resolve_authenticated_user_or_raise(authorization: str | None) -> str:
    token = parse_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_or_invalid_token")
    user_id = resolve_authenticated_user(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_expired_token")
    return user_id


def _parse_admin_users_env(raw_value: str) -> set[str]:
    values = [item.strip() for item in raw_value.split(",")]
    return {item for item in values if item}
