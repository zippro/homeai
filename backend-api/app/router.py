from __future__ import annotations

from app.schemas import ImagePart, OperationType, ProviderSettings, RenderTier


def _rule_provider_for_tier(rule_preview_provider: str, rule_final_provider: str, tier: RenderTier) -> str:
    return rule_preview_provider if tier == RenderTier.preview else rule_final_provider


def resolve_provider_candidates(
    settings: ProviderSettings,
    operation: OperationType,
    tier: RenderTier,
    target_parts: list[ImagePart],
    available_providers: set[str],
) -> list[str]:
    candidates: list[str] = []

    # If user edits one specific part, prefer the part-level route.
    if len(target_parts) == 1:
        part = target_parts[0]
        part_rule = settings.part_routes.get(part)
        if part_rule:
            candidates.append(
                _rule_provider_for_tier(part_rule.preview_provider, part_rule.final_provider, tier)
            )

    op_rule = settings.operation_routes.get(operation)
    if op_rule:
        candidates.append(_rule_provider_for_tier(op_rule.preview_provider, op_rule.final_provider, tier))

    candidates.extend([settings.default_provider, *settings.fallback_chain])

    deduplicated: list[str] = []
    for provider_name in candidates:
        if provider_name not in deduplicated:
            deduplicated.append(provider_name)

    filtered = [
        provider_name
        for provider_name in deduplicated
        if provider_name in settings.enabled_providers and provider_name in available_providers
    ]

    if not filtered:
        raise ValueError("No enabled provider is available for this route")

    return filtered


def resolve_provider(
    settings: ProviderSettings,
    operation: OperationType,
    tier: RenderTier,
    target_parts: list[ImagePart],
    available_providers: set[str],
) -> str:
    return resolve_provider_candidates(
        settings=settings,
        operation=operation,
        tier=tier,
        target_parts=target_parts,
        available_providers=available_providers,
    )[0]


def resolve_model(settings: ProviderSettings, provider_name: str, tier: RenderTier) -> str:
    provider_cfg = settings.provider_models.get(provider_name)
    if not provider_cfg:
        raise ValueError(f"Missing provider model config for {provider_name}")
    return provider_cfg.preview_model if tier == RenderTier.preview else provider_cfg.final_model
