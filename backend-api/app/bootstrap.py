from __future__ import annotations

from app.db import Base, engine
from app.models import (  # noqa: F401
    AdminAuditLogModel,
    AnalyticsEventModel,
    CreditBalanceModel,
    CreditLedgerEntryModel,
    CreditResetScheduleModel,
    PlanModel,
    ProviderSettingsStateModel,
    ProviderSettingsVersionModel,
    RenderJobModel,
    SubscriptionEntitlementModel,
    SubscriptionWebhookEventModel,
    UserProjectModel,
    VariableModel,
)
from app.credit_reset_store import bootstrap_credit_reset_schedule
from app.product_store import bootstrap_product_data
from app.settings_store import bootstrap_provider_settings


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    bootstrap_provider_settings()
    bootstrap_product_data()
    bootstrap_credit_reset_schedule()
