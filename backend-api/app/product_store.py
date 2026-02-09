from __future__ import annotations

from datetime import datetime
from app.time_utils import utc_now

from sqlalchemy import desc, select

from app.db import session_scope
from app.models import AdminAuditLogModel, PlanModel, VariableModel
from app.schemas import AdminActionRequest, AppVariable, AuditLogEntry, PlanConfig, PlanUpsertRequest, VariableUpsertRequest

_PRODUCT_DOMAIN = "product"

_DEFAULT_PLANS: dict[str, PlanConfig] = {
    "free": PlanConfig(
        plan_id="free",
        display_name="Free",
        is_active=True,
        daily_credits=3,
        preview_cost_credits=1,
        final_cost_credits=2,
        monthly_price_usd=0,
        features=["daily_free_credits", "preview_generation"],
    ),
    "pro": PlanConfig(
        plan_id="pro",
        display_name="Pro",
        is_active=True,
        daily_credits=80,
        preview_cost_credits=1,
        final_cost_credits=1,
        monthly_price_usd=14.99,
        ios_product_id="pro_monthly_ios",
        android_product_id="pro_monthly_android",
        web_product_id="pro_monthly_web",
        features=["higher_limits", "priority_queue", "no_ads"],
    ),
}

_DEFAULT_VARIABLES: dict[str, AppVariable] = {
    "daily_credit_limit_enabled": AppVariable(
        key="daily_credit_limit_enabled",
        value=True,
        description="Enable or disable daily credit cap enforcement",
    ),
    "preview_before_final_required": AppVariable(
        key="preview_before_final_required",
        value=True,
        description="Require preview completion before final render",
    ),
}


def bootstrap_product_data() -> None:
    with session_scope() as session:
        has_plans = session.execute(select(PlanModel.plan_id).limit(1)).first()
        if not has_plans:
            for plan in _DEFAULT_PLANS.values():
                session.add(
                    PlanModel(
                        plan_id=plan.plan_id,
                        payload_json=plan.model_dump(mode="json"),
                        is_active=plan.is_active,
                    )
                )

        has_vars = session.execute(select(VariableModel.key).limit(1)).first()
        if not has_vars:
            for var in _DEFAULT_VARIABLES.values():
                session.add(
                    VariableModel(
                        key=var.key,
                        value_json=var.value,
                        description=var.description,
                    )
                )


def list_plans() -> list[PlanConfig]:
    with session_scope() as session:
        rows = session.execute(select(PlanModel)).scalars().all()
        return [PlanConfig.model_validate(row.payload_json) for row in rows]


def get_plan(plan_id: str) -> PlanConfig | None:
    with session_scope() as session:
        model = session.get(PlanModel, plan_id)
        if not model:
            return None
        return PlanConfig.model_validate(model.payload_json)


def upsert_plan(plan_id: str, payload: PlanUpsertRequest, action: AdminActionRequest) -> PlanConfig:
    plan = PlanConfig(plan_id=plan_id, **payload.model_dump())

    with session_scope() as session:
        existing = session.get(PlanModel, plan_id)
        if existing:
            existing.payload_json = plan.model_dump(mode="json")
            existing.is_active = plan.is_active
            existing.updated_at = utc_now()
        else:
            session.add(
                PlanModel(
                    plan_id=plan_id,
                    payload_json=plan.model_dump(mode="json"),
                    is_active=plan.is_active,
                    updated_at=utc_now(),
                )
            )

        _append_audit(
            session=session,
            action="plan_upserted",
            actor=action.actor,
            reason=action.reason,
            metadata={"plan_id": plan_id},
        )

    return plan


def delete_plan(plan_id: str, action: AdminActionRequest) -> bool:
    with session_scope() as session:
        existing = session.get(PlanModel, plan_id)
        if not existing:
            return False

        session.delete(existing)
        _append_audit(
            session=session,
            action="plan_deleted",
            actor=action.actor,
            reason=action.reason,
            metadata={"plan_id": plan_id},
        )

    return True


def list_variables() -> list[AppVariable]:
    with session_scope() as session:
        rows = session.execute(select(VariableModel)).scalars().all()
        return [
            AppVariable(
                key=row.key,
                value=row.value_json,
                description=row.description,
            )
            for row in rows
        ]


def get_variable_map() -> dict[str, str | int | float | bool]:
    with session_scope() as session:
        rows = session.execute(select(VariableModel)).scalars().all()
        return {row.key: row.value_json for row in rows}


def upsert_variable(key: str, payload: VariableUpsertRequest, action: AdminActionRequest) -> AppVariable:
    with session_scope() as session:
        existing = session.get(VariableModel, key)
        if existing:
            existing.value_json = payload.value
            existing.description = payload.description
            existing.updated_at = utc_now()
        else:
            session.add(
                VariableModel(
                    key=key,
                    value_json=payload.value,
                    description=payload.description,
                    updated_at=utc_now(),
                )
            )

        _append_audit(
            session=session,
            action="variable_upserted",
            actor=action.actor,
            reason=action.reason,
            metadata={"key": key},
        )

    return AppVariable(key=key, value=payload.value, description=payload.description)


def delete_variable(key: str, action: AdminActionRequest) -> bool:
    with session_scope() as session:
        existing = session.get(VariableModel, key)
        if not existing:
            return False

        session.delete(existing)
        _append_audit(
            session=session,
            action="variable_deleted",
            actor=action.actor,
            reason=action.reason,
            metadata={"key": key},
        )

    return True


def list_product_audit(limit: int = 100) -> list[AuditLogEntry]:
    with session_scope() as session:
        stmt = (
            select(AdminAuditLogModel)
            .where(AdminAuditLogModel.domain == _PRODUCT_DOMAIN)
            .order_by(desc(AdminAuditLogModel.created_at))
            .limit(limit)
        )
        rows = session.execute(stmt).scalars().all()
        return [
            AuditLogEntry(
                id=row.id,
                action=row.action,
                actor=row.actor,
                reason=row.reason,
                created_at=row.created_at,
                metadata=row.metadata_json or {},
            )
            for row in rows
        ]


def _append_audit(
    session,
    action: str,
    actor: str,
    reason: str | None,
    metadata: dict,
) -> None:
    entry = AuditLogEntry(
        action=action,
        actor=actor,
        reason=reason,
        metadata=metadata,
    )
    session.add(
        AdminAuditLogModel(
            id=entry.id,
            domain=_PRODUCT_DOMAIN,
            action=entry.action,
            actor=entry.actor,
            reason=entry.reason,
            metadata_json=entry.metadata,
            created_at=entry.created_at,
        )
    )
