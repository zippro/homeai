from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.auth_utils import parse_bearer_token
from app.auth_store import create_dev_session, get_me, revoke_session
from app.schemas import AuthMeResponse, AuthSessionResponse, DevLoginRequest, LogoutResponse

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login-dev", response_model=AuthSessionResponse)
async def login_dev(payload: DevLoginRequest) -> AuthSessionResponse:
    return create_dev_session(payload)


@router.get("/me", response_model=AuthMeResponse)
async def auth_me(authorization: str | None = Header(default=None)) -> AuthMeResponse:
    token = parse_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_or_invalid_token")
    me = get_me(token)
    if not me:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_expired_token")
    return me


@router.post("/logout", response_model=LogoutResponse)
async def logout(authorization: str | None = Header(default=None)) -> LogoutResponse:
    token = parse_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_or_invalid_token")
    return revoke_session(token)
