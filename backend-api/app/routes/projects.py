from __future__ import annotations

from fastapi import APIRouter, Query

from app.job_store import get_user_board
from app.schemas import UserBoardResponse

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("/board/{user_id}", response_model=UserBoardResponse)
async def user_board(user_id: str, limit: int = Query(default=30, ge=1, le=100)) -> UserBoardResponse:
    return get_user_board(user_id=user_id, limit=limit)
