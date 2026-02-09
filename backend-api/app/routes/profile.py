from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import assert_same_user, get_authenticated_user
from app.profile_store import get_profile_overview
from app.schemas import ProfileOverviewResponse

router = APIRouter(prefix="/v1/profile", tags=["profile"])


@router.get("/overview/me", response_model=ProfileOverviewResponse)
async def profile_overview_me(auth_user_id: str = Depends(get_authenticated_user)) -> ProfileOverviewResponse:
    return get_profile_overview(auth_user_id)


@router.get("/overview/{user_id}", response_model=ProfileOverviewResponse)
async def profile_overview(
    user_id: str,
    auth_user_id: str = Depends(get_authenticated_user),
) -> ProfileOverviewResponse:
    assert_same_user(auth_user_id, user_id)
    return get_profile_overview(user_id)
