from __future__ import annotations

from app.credit_reset_store import get_credit_reset_schedule
from app.credit_store import get_balance
from app.product_store import get_plan
from app.schemas import PlanConfig, ProfileOverviewResponse
from app.subscription_store import get_entitlement


def get_profile_overview(user_id: str) -> ProfileOverviewResponse:
    credits = get_balance(user_id)
    entitlement = get_entitlement(user_id)
    schedule = get_credit_reset_schedule()

    effective_plan_id = entitlement.plan_id if entitlement.status.value == "active" else "free"
    effective_plan = get_plan(effective_plan_id) or PlanConfig(
        plan_id="free",
        display_name="Free",
        is_active=True,
        daily_credits=3,
        preview_cost_credits=1,
        final_cost_credits=2,
        monthly_price_usd=0,
        features=["daily_free_credits", "preview_generation"],
    )

    return ProfileOverviewResponse(
        user_id=user_id,
        credits=credits,
        entitlement=entitlement,
        effective_plan=effective_plan,
        next_credit_reset_at=schedule.next_run_at,
    )
