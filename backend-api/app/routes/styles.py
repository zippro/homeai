from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.product_store import get_style, list_styles
from app.schemas import StylePreset

router = APIRouter(prefix="/v1/styles", tags=["styles"])


@router.get("", response_model=list[StylePreset])
async def get_styles(active_only: bool = Query(default=True)) -> list[StylePreset]:
    return list_styles(active_only=active_only)


@router.get("/{style_id}", response_model=StylePreset)
async def get_style_by_id(style_id: str) -> StylePreset:
    style = get_style(style_id)
    if not style:
        raise HTTPException(status_code=404, detail="style_not_found")
    return style

