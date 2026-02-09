from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import assert_same_user, get_authenticated_user
from app.job_store import get_user_board
from app.schemas import UserBoardResponse

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("/board/me", response_model=UserBoardResponse)
async def my_board(
    limit: int = Query(default=30, ge=1, le=100),
    auth_user_id: str = Depends(get_authenticated_user),
) -> UserBoardResponse:
    return get_user_board(user_id=auth_user_id, limit=limit)


@router.get("/board/{user_id}", response_model=UserBoardResponse)
async def user_board(
    user_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    auth_user_id: str = Depends(get_authenticated_user),
) -> UserBoardResponse:
    assert_same_user(auth_user_id, user_id)
    return get_user_board(user_id=user_id, limit=limit)
