from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.providers.registry import get_provider_registry
from app.product_store import get_variable_map, list_active_styles, list_plans
from app.router import resolve_model, resolve_provider_candidates
from app.schemas import ImagePart, MobileBootstrapConfigResponse, OperationType, ProviderRoutePreviewResponse, RenderTier
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


@router.get("/provider-route-preview", response_model=ProviderRoutePreviewResponse)
async def get_provider_route_preview(
    operation: OperationType = Query(default=OperationType.restyle),
    tier: RenderTier = Query(default=RenderTier.preview),
    target_part: ImagePart = Query(default=ImagePart.full_room),
) -> ProviderRoutePreviewResponse:
    settings = get_provider_settings()
    provider_meta = get_provider_settings_meta()
    registry = get_provider_registry()
    available_providers = set(registry.keys())

    try:
        candidates = resolve_provider_candidates(
            settings=settings,
            operation=operation,
            tier=tier,
            target_parts=[target_part],
            available_providers=available_providers,
        )
        selected_provider = candidates[0]
        selected_model = resolve_model(settings=settings, provider_name=selected_provider, tier=tier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ProviderRoutePreviewResponse(
        operation=operation,
        tier=tier,
        target_parts=[target_part],
        candidate_chain=candidates,
        selected_provider=selected_provider,
        selected_model=selected_model,
        settings_version=provider_meta.get("current_version"),
    )
