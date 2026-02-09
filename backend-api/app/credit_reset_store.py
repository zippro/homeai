from __future__ import annotations

from datetime import datetime, timedelta
from app.time_utils import utc_now

from sqlalchemy import select

from app.db import session_scope
from app.models import CreditBalanceModel, CreditLedgerEntryModel, CreditResetScheduleModel, SubscriptionEntitlementModel
from app.product_store import list_plans
from app.schemas import (
    CreditResetRunResponse,
    CreditResetScheduleResponse,
    CreditResetScheduleUpdateRequest,
    CreditResetTickResponse,
)

_SCHEDULE_ID = 1


def bootstrap_credit_reset_schedule() -> None:
    with session_scope() as session:
        schedule = session.get(CreditResetScheduleModel, _SCHEDULE_ID)
        if schedule:
            return

        now = utc_now()
        schedule = CreditResetScheduleModel(
            id=_SCHEDULE_ID,
            enabled=True,
            reset_hour_utc=0,
            reset_minute_utc=0,
            free_daily_credits=3,
            pro_daily_credits=80,
            last_run_at=None,
            next_run_at=_compute_next_run(0, 0, now),
        )
        session.add(schedule)


def get_credit_reset_schedule() -> CreditResetScheduleResponse:
    with session_scope() as session:
        schedule = _get_or_create_schedule(session)
        return _to_schema(schedule)


def update_credit_reset_schedule(payload: CreditResetScheduleUpdateRequest) -> CreditResetScheduleResponse:
    with session_scope() as session:
        schedule = _get_or_create_schedule(session)
        update_data = payload.model_dump(exclude_none=True)

        if "enabled" in update_data:
            schedule.enabled = bool(update_data["enabled"])
        if "reset_hour_utc" in update_data:
            schedule.reset_hour_utc = int(update_data["reset_hour_utc"])
        if "reset_minute_utc" in update_data:
            schedule.reset_minute_utc = int(update_data["reset_minute_utc"])
        if "free_daily_credits" in update_data:
            schedule.free_daily_credits = int(update_data["free_daily_credits"])
        if "pro_daily_credits" in update_data:
            schedule.pro_daily_credits = int(update_data["pro_daily_credits"])

        schedule.next_run_at = _compute_next_run(schedule.reset_hour_utc, schedule.reset_minute_utc, utc_now())
        schedule.updated_at = utc_now()

        return _to_schema(schedule)


def run_daily_credit_reset(dry_run: bool = False, run_at: datetime | None = None) -> CreditResetRunResponse:
    started_at = run_at or utc_now()

    with session_scope() as session:
        schedule = _get_or_create_schedule(session)

        plan_daily_credits = {plan.plan_id: plan.daily_credits for plan in list_plans()}

        balance_users = set(session.execute(select(CreditBalanceModel.user_id)).scalars().all())
        entitlement_users = set(session.execute(select(SubscriptionEntitlementModel.user_id)).scalars().all())
        user_ids = sorted(balance_users | entitlement_users)

        balances_updated = 0
        for user_id in user_ids:
            entitlement = session.get(SubscriptionEntitlementModel, user_id)
            plan_id = (
                entitlement.plan_id
                if entitlement and entitlement.status == "active" and entitlement.plan_id
                else "free"
            )

            target_balance = _resolve_target_balance(plan_id, plan_daily_credits, schedule)
            balance_model = session.get(CreditBalanceModel, user_id)
            if not balance_model:
                balance_model = CreditBalanceModel(user_id=user_id, balance=0)
                session.add(balance_model)

            current_balance = balance_model.balance
            delta = target_balance - current_balance

            if delta == 0:
                continue

            idempotency_key = f"daily_reset:{started_at.date().isoformat()}:{user_id}"
            existing_entry = session.execute(
                select(CreditLedgerEntryModel).where(CreditLedgerEntryModel.idempotency_key == idempotency_key)
            ).scalar_one_or_none()
            if existing_entry:
                continue

            balances_updated += 1
            if dry_run:
                continue

            balance_model.balance = target_balance
            balance_model.updated_at = utc_now()

            session.add(
                CreditLedgerEntryModel(
                    user_id=user_id,
                    delta=delta,
                    reason="daily_reset",
                    idempotency_key=idempotency_key,
                    metadata_json={
                        "plan_id": plan_id,
                        "target_balance": target_balance,
                    },
                )
            )

        if not dry_run:
            schedule.last_run_at = started_at
            schedule.next_run_at = _compute_next_run(schedule.reset_hour_utc, schedule.reset_minute_utc, started_at)
            schedule.updated_at = utc_now()

    completed_at = utc_now()
    return CreditResetRunResponse(
        started_at=started_at,
        completed_at=completed_at,
        dry_run=dry_run,
        users_processed=len(user_ids),
        balances_updated=balances_updated,
    )


def tick_daily_credit_reset() -> CreditResetTickResponse:
    checked_at = utc_now()

    with session_scope() as session:
        schedule = _get_or_create_schedule(session)
        if not schedule.enabled:
            return CreditResetTickResponse(
                checked_at=checked_at,
                due=False,
                ran=False,
                skipped_reason="disabled",
                run_result=None,
            )

        next_run_at = schedule.next_run_at or _compute_next_run(
            schedule.reset_hour_utc,
            schedule.reset_minute_utc,
            checked_at,
        )
        if checked_at < next_run_at:
            return CreditResetTickResponse(
                checked_at=checked_at,
                due=False,
                ran=False,
                skipped_reason="not_due",
                run_result=None,
            )

    run_result = run_daily_credit_reset(dry_run=False, run_at=checked_at)
    return CreditResetTickResponse(
        checked_at=checked_at,
        due=True,
        ran=True,
        skipped_reason=None,
        run_result=run_result,
    )


def _resolve_target_balance(
    plan_id: str,
    plan_daily_credits: dict[str, int],
    schedule: CreditResetScheduleModel,
) -> int:
    if plan_id == "free":
        return schedule.free_daily_credits
    if plan_id == "pro":
        return schedule.pro_daily_credits
    return plan_daily_credits.get(plan_id, schedule.free_daily_credits)


def _get_or_create_schedule(session) -> CreditResetScheduleModel:
    schedule = session.get(CreditResetScheduleModel, _SCHEDULE_ID)
    if schedule:
        return schedule

    now = utc_now()
    schedule = CreditResetScheduleModel(
        id=_SCHEDULE_ID,
        enabled=True,
        reset_hour_utc=0,
        reset_minute_utc=0,
        free_daily_credits=3,
        pro_daily_credits=80,
        next_run_at=_compute_next_run(0, 0, now),
    )
    session.add(schedule)
    return schedule


def _compute_next_run(hour: int, minute: int, reference: datetime) -> datetime:
    candidate = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= reference:
        candidate = candidate + timedelta(days=1)
    return candidate


def _to_schema(schedule: CreditResetScheduleModel) -> CreditResetScheduleResponse:
    return CreditResetScheduleResponse(
        enabled=schedule.enabled,
        reset_hour_utc=schedule.reset_hour_utc,
        reset_minute_utc=schedule.reset_minute_utc,
        free_daily_credits=schedule.free_daily_credits,
        pro_daily_credits=schedule.pro_daily_credits,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
    )
