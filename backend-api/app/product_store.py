from __future__ import annotations

from app.time_utils import utc_now

from sqlalchemy import desc, select

from app.db import session_scope
from app.models import AdminAuditLogModel, PlanModel, StyleModel, VariableModel
from app.schemas import (
    AdminActionRequest,
    AppVariable,
    AuditLogEntry,
    PlanConfig,
    PlanUpsertRequest,
    StylePreset,
    StyleUpsertRequest,
    VariableUpsertRequest,
)

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

_DEFAULT_STYLES: dict[str, StylePreset] = {
    "modern": StylePreset(
        style_id="modern",
        display_name="Modern",
        prompt=(
            "Modern clean interior design with balanced composition, natural daylight, premium materials, "
            "and minimal visual clutter."
        ),
        thumbnail_url="https://picsum.photos/id/1068/900/900",
        tags=["clean", "contemporary"],
        room_types=["living_room", "bedroom", "kitchen"],
        sort_order=10,
    ),
    "minimalistic": StylePreset(
        style_id="minimalistic",
        display_name="Minimalistic",
        prompt="Minimalist interior with uncluttered surfaces, neutral palette, and calm airy atmosphere.",
        thumbnail_url="https://picsum.photos/id/1059/900/900",
        tags=["minimal", "neutral"],
        room_types=["living_room", "bedroom", "home_office"],
        sort_order=20,
    ),
    "bohemian": StylePreset(
        style_id="bohemian",
        display_name="Bohemian",
        prompt="Bohemian interior with layered textiles, handcrafted decor, earthy tones, and eclectic accents.",
        thumbnail_url="https://picsum.photos/id/1044/900/900",
        tags=["warm", "eclectic"],
        room_types=["living_room", "bedroom", "coffee_shop"],
        sort_order=30,
    ),
    "scandinavian": StylePreset(
        style_id="scandinavian",
        display_name="Scandinavian",
        prompt="Scandinavian interior with warm oak details, white walls, cozy textiles, and soft daylight.",
        thumbnail_url="https://picsum.photos/id/1025/900/900",
        tags=["nordic", "bright"],
        room_types=["living_room", "bedroom", "kitchen"],
        sort_order=40,
    ),
    "industrial": StylePreset(
        style_id="industrial",
        display_name="Industrial",
        prompt="Industrial loft style with exposed materials, black metal accents, and cinematic contrast.",
        thumbnail_url="https://picsum.photos/id/1067/900/900",
        tags=["loft", "urban"],
        room_types=["living_room", "home_office", "restaurant"],
        sort_order=50,
    ),
    "japandi": StylePreset(
        style_id="japandi",
        display_name="Japandi",
        prompt="Japandi interior with serene palette, organic forms, low furniture, and tactile natural textures.",
        thumbnail_url="https://picsum.photos/id/1015/900/900",
        tags=["calm", "organic"],
        room_types=["living_room", "bedroom", "home_office"],
        sort_order=60,
    ),
    "rustic": StylePreset(
        style_id="rustic",
        display_name="Rustic",
        prompt="Rustic interior with weathered wood, warm ambient lighting, and handcrafted cozy details.",
        thumbnail_url="https://picsum.photos/id/1008/900/900",
        tags=["cozy", "natural"],
        room_types=["living_room", "dining_room"],
        sort_order=70,
    ),
    "vintage": StylePreset(
        style_id="vintage",
        display_name="Vintage",
        prompt="Vintage-inspired interior with classic silhouettes, rich details, and timeless character.",
        thumbnail_url="https://picsum.photos/id/1074/900/900",
        tags=["classic", "heritage"],
        room_types=["living_room", "study_room", "restaurant"],
        sort_order=80,
    ),
    "christmas": StylePreset(
        style_id="christmas",
        display_name="Christmas",
        prompt="Festive Christmas interior with warm lights, seasonal decor, and cozy holiday atmosphere.",
        thumbnail_url="https://picsum.photos/id/1041/900/900",
        tags=["seasonal", "festive"],
        room_types=["living_room", "exterior"],
        sort_order=90,
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

        has_styles = session.execute(select(StyleModel.style_id).limit(1)).first()
        if not has_styles:
            for style in _DEFAULT_STYLES.values():
                session.add(
                    StyleModel(
                        style_id=style.style_id,
                        payload_json=style.model_dump(mode="json"),
                        is_active=style.is_active,
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


def list_styles(active_only: bool = False) -> list[StylePreset]:
    with session_scope() as session:
        stmt = select(StyleModel)
        if active_only:
            stmt = stmt.where(StyleModel.is_active.is_(True))
        rows = session.execute(stmt).scalars().all()
        styles = [StylePreset.model_validate(row.payload_json) for row in rows]
        return sorted(
            styles,
            key=lambda item: (
                int(item.sort_order or 0),
                item.display_name.lower(),
                item.style_id.lower(),
            ),
        )


def list_active_styles() -> list[StylePreset]:
    return list_styles(active_only=True)


def get_style(style_id: str) -> StylePreset | None:
    with session_scope() as session:
        model = session.get(StyleModel, style_id)
        if not model:
            return None
        return StylePreset.model_validate(model.payload_json)


def upsert_style(style_id: str, payload: StyleUpsertRequest, action: AdminActionRequest) -> StylePreset:
    style = StylePreset(style_id=style_id, **payload.model_dump())

    with session_scope() as session:
        existing = session.get(StyleModel, style_id)
        if existing:
            existing.payload_json = style.model_dump(mode="json")
            existing.is_active = style.is_active
            existing.updated_at = utc_now()
        else:
            session.add(
                StyleModel(
                    style_id=style_id,
                    payload_json=style.model_dump(mode="json"),
                    is_active=style.is_active,
                    updated_at=utc_now(),
                )
            )

        _append_audit(
            session=session,
            action="style_upserted",
            actor=action.actor,
            reason=action.reason,
            metadata={"style_id": style_id},
        )

    return style


def delete_style(style_id: str, action: AdminActionRequest) -> bool:
    with session_scope() as session:
        existing = session.get(StyleModel, style_id)
        if not existing:
            return False

        session.delete(existing)
        _append_audit(
            session=session,
            action="style_deleted",
            actor=action.actor,
            reason=action.reason,
            metadata={"style_id": style_id},
        )

    return True


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
