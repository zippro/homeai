from __future__ import annotations

def _tier_value(tier: object) -> str:
    if hasattr(tier, "value"):
        return str(getattr(tier, "value"))
    return str(tier)


def resolve_credit_cost(preview_cost_credits: int, final_cost_credits: int, tier: object) -> int:
    if _tier_value(tier) == "preview":
        return max(0, int(preview_cost_credits))
    return max(0, int(final_cost_credits))


def should_block_final_without_preview(
    *,
    preview_before_final_required: bool,
    tier: object,
    has_completed_preview: bool,
) -> bool:
    if not preview_before_final_required:
        return False
    if _tier_value(tier) != "final":
        return False
    return not has_completed_preview
