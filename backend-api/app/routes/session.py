from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.auth import get_authenticated_user
from app.auth_store import get_me
from app.auth_utils import parse_bearer_token
from app.experiment_store import assign_active_experiments_for_user
from app.job_store import get_user_board
from app.product_store import get_variable_map, list_plans
from app.profile_store import get_profile_overview
from app.schemas import ActiveExperimentAssignmentsResponse, SessionBootstrapResponse
from app.settings_store import get_provider_settings, get_provider_settings_meta

router = APIRouter(prefix="/v1/session", tags=["session"])


@router.get("/bootstrap/me", response_model=SessionBootstrapResponse)
async def session_bootstrap_me(
    board_limit: int = Query(default=30, ge=1, le=100),
    experiment_limit: int = Query(default=50, ge=1, le=200),
    authorization: str | None = Header(default=None),
    auth_user_id: str = Depends(get_authenticated_user),
) -> SessionBootstrapResponse:
    token = parse_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_or_invalid_token")
    me = get_me(token)
    if not me:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_expired_token")

    profile = get_profile_overview(auth_user_id)
    board = get_user_board(user_id=auth_user_id, limit=board_limit)
    assignments = assign_active_experiments_for_user(user_id=auth_user_id, limit=experiment_limit)
    experiments = ActiveExperimentAssignmentsResponse(user_id=auth_user_id, assignments=assignments)
    catalog = [plan for plan in list_plans() if plan.is_active]

    provider_settings = get_provider_settings()
    provider_meta = get_provider_settings_meta()
    provider_defaults = {
        "default_provider": provider_settings.default_provider,
        "fallback_chain": provider_settings.fallback_chain,
        "version": provider_meta["current_version"],
    }

    return SessionBootstrapResponse(
        me=me,
        profile=profile,
        board=board,
        experiments=experiments,
        catalog=catalog,
        variables=get_variable_map(),
        provider_defaults=provider_defaults,
    )

