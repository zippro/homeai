from __future__ import annotations

from fastapi import APIRouter

from app.product_store import get_variable_map, list_active_styles, list_plans
from app.schemas import MobileBootstrapConfigResponse
from app.settings_store import get_provider_settings, get_provider_settings_meta

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("/bootstrap", response_model=MobileBootstrapConfigResponse)
async def get_mobile_bootstrap_config() -> MobileBootstrapConfigResponse:
    plans = [plan for plan in list_plans() if plan.is_active]
    styles = list_active_styles()
    variables = get_variable_map()

    provider_settings = get_provider_settings()
    provider_meta = get_provider_settings_meta()

    provider_defaults = {
        "default_provider": provider_settings.default_provider,
        "fallback_chain": provider_settings.fallback_chain,
        "version": provider_meta["current_version"],
    }

    return MobileBootstrapConfigResponse(
        active_plans=plans,
        styles=styles,
        variables=variables,
        provider_defaults=provider_defaults,
    )
