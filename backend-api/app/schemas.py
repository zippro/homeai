from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl

ScalarValue = str | int | float | bool


class OperationType(str, Enum):
    restyle = "restyle"
    replace = "replace"
    remove = "remove"
    repaint = "repaint"


class RenderTier(str, Enum):
    preview = "preview"
    final = "final"


class ImagePart(str, Enum):
    full_room = "full_room"
    walls = "walls"
    floor = "floor"
    furniture = "furniture"
    decor = "decor"


class JobStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class RouteRule(BaseModel):
    preview_provider: str
    final_provider: str


class ProviderModelConfig(BaseModel):
    preview_model: str
    final_model: str


class CostControlSettings(BaseModel):
    max_retries: int = 1
    max_output_megapixels: float = 1.2
    preview_required_before_final: bool = True


class ProviderSettings(BaseModel):
    default_provider: str = "fal"
    enabled_providers: list[str] = Field(default_factory=lambda: ["fal", "openai"])
    fallback_chain: list[str] = Field(default_factory=lambda: ["fal", "openai"])
    operation_routes: dict[OperationType, RouteRule] = Field(
        default_factory=lambda: {
            OperationType.restyle: RouteRule(preview_provider="fal", final_provider="fal"),
            OperationType.replace: RouteRule(preview_provider="fal", final_provider="fal"),
            OperationType.remove: RouteRule(preview_provider="fal", final_provider="fal"),
            OperationType.repaint: RouteRule(preview_provider="fal", final_provider="fal"),
        }
    )
    part_routes: dict[ImagePart, RouteRule] = Field(
        default_factory=lambda: {
            ImagePart.full_room: RouteRule(preview_provider="fal", final_provider="fal"),
            ImagePart.walls: RouteRule(preview_provider="fal", final_provider="fal"),
            ImagePart.floor: RouteRule(preview_provider="fal", final_provider="fal"),
            ImagePart.furniture: RouteRule(preview_provider="fal", final_provider="fal"),
            ImagePart.decor: RouteRule(preview_provider="fal", final_provider="fal"),
        }
    )
    provider_models: dict[str, ProviderModelConfig] = Field(
        default_factory=lambda: {
            "fal": ProviderModelConfig(
                preview_model="fal-ai/flux-1/schnell",
                final_model="fal-ai/flux-pro/kontext",
            ),
            "openai": ProviderModelConfig(
                preview_model="gpt-image-1-mini",
                final_model="gpt-image-1",
            ),
            "mock": ProviderModelConfig(
                preview_model="mock-preview",
                final_model="mock-final",
            ),
        }
    )
    cost_controls: CostControlSettings = Field(default_factory=CostControlSettings)


class ProviderSettingsUpdateRequest(BaseModel):
    default_provider: str | None = None
    enabled_providers: list[str] | None = None
    fallback_chain: list[str] | None = None
    operation_routes: dict[OperationType, RouteRule] | None = None
    part_routes: dict[ImagePart, RouteRule] | None = None
    provider_models: dict[str, ProviderModelConfig] | None = None
    cost_controls: CostControlSettings | None = None


class AdminActionRequest(BaseModel):
    actor: str = "dashboard"
    reason: str | None = None


class ProviderSettingsVersionSummary(BaseModel):
    version: int
    actor: str
    reason: str | None
    created_at: datetime


class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    actor: str
    reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanConfig(BaseModel):
    plan_id: str
    display_name: str
    is_active: bool = True
    daily_credits: int = Field(default=0, ge=0)
    preview_cost_credits: int = Field(default=1, ge=0)
    final_cost_credits: int = Field(default=2, ge=0)
    monthly_price_usd: float = Field(default=0.0, ge=0)
    ios_product_id: str | None = None
    android_product_id: str | None = None
    features: list[str] = Field(default_factory=list)


class PlanUpsertRequest(BaseModel):
    display_name: str
    is_active: bool = True
    daily_credits: int = Field(default=0, ge=0)
    preview_cost_credits: int = Field(default=1, ge=0)
    final_cost_credits: int = Field(default=2, ge=0)
    monthly_price_usd: float = Field(default=0.0, ge=0)
    ios_product_id: str | None = None
    android_product_id: str | None = None
    features: list[str] = Field(default_factory=list)


class AppVariable(BaseModel):
    key: str
    value: ScalarValue
    description: str | None = None


class VariableUpsertRequest(BaseModel):
    value: ScalarValue
    description: str | None = None


class AnalyticsEventRequest(BaseModel):
    event_name: str
    user_id: str | None = None
    platform: str | None = None
    provider: str | None = None
    operation: OperationType | None = None
    status: JobStatus | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsOverviewResponse(BaseModel):
    total_events: int
    render_events: int
    render_success: int
    render_failed: int
    render_success_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_cost_usd: float
    provider_event_counts: dict[str, int]
    provider_success_rate: dict[str, float]


class RenderJobCreateRequest(BaseModel):
    user_id: str | None = None
    project_id: str
    image_url: HttpUrl
    style_id: str
    operation: OperationType
    tier: RenderTier = RenderTier.preview
    target_parts: list[ImagePart] = Field(default_factory=lambda: [ImagePart.full_room])
    mask_url: HttpUrl | None = None
    prompt_overrides: dict[str, Any] = Field(default_factory=dict)


class ProviderDispatchRequest(BaseModel):
    prompt: str
    image_url: HttpUrl
    mask_url: HttpUrl | None
    model_id: str
    operation: OperationType
    tier: RenderTier
    target_parts: list[ImagePart]


class ProviderDispatchResult(BaseModel):
    provider_job_id: str
    status: JobStatus
    output_url: HttpUrl | None = None
    estimated_cost_usd: float = 0.0


class ProviderStatusResult(BaseModel):
    status: JobStatus
    output_url: HttpUrl | None = None
    error_code: str | None = None


class RenderJobRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    style_id: str
    operation: OperationType
    tier: RenderTier
    target_parts: list[ImagePart]
    provider: str
    provider_model: str
    provider_attempts: list[str] = Field(default_factory=list)
    provider_job_id: str
    status: JobStatus
    output_url: HttpUrl | None = None
    estimated_cost_usd: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_code: str | None = None


class RenderJobStatusResponse(BaseModel):
    id: str
    status: JobStatus
    provider: str
    provider_model: str
    output_url: HttpUrl | None
    estimated_cost_usd: float
    updated_at: datetime
    error_code: str | None


class ProjectBoardItemResponse(BaseModel):
    project_id: str
    cover_image_url: HttpUrl | None = None
    generation_count: int
    last_job_id: str | None = None
    last_style_id: str | None = None
    last_status: JobStatus | None = None
    last_output_url: HttpUrl | None = None
    last_updated_at: datetime | None = None


class UserBoardResponse(BaseModel):
    user_id: str
    projects: list[ProjectBoardItemResponse]


class DiscoverItem(BaseModel):
    id: str
    title: str
    subtitle: str
    category: str
    before_image_url: HttpUrl
    after_image_url: HttpUrl


class DiscoverSection(BaseModel):
    key: str
    title: str
    items: list[DiscoverItem]


class DiscoverFeedResponse(BaseModel):
    tabs: list[str]
    sections: list[DiscoverSection]


class CancelJobResponse(BaseModel):
    id: str
    canceled: bool
    status: JobStatus


class EventIngestResponse(BaseModel):
    accepted: bool


class MobileBootstrapConfigResponse(BaseModel):
    active_plans: list[PlanConfig]
    variables: dict[str, ScalarValue]
    provider_defaults: dict[str, Any]


class CreditBalanceResponse(BaseModel):
    user_id: str
    balance: int


class CreditConsumeRequest(BaseModel):
    user_id: str
    amount: int = Field(ge=1)
    reason: str = "render"
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreditGrantRequest(BaseModel):
    user_id: str
    amount: int = Field(ge=1)
    reason: str = "daily_reset"
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreditOperationResponse(BaseModel):
    user_id: str
    balance: int
    applied: bool


class SubscriptionSource(str, Enum):
    ios = "ios"
    android = "android"
    manual = "manual"


class SubscriptionStatus(str, Enum):
    active = "active"
    canceled = "canceled"
    expired = "expired"
    inactive = "inactive"


class SubscriptionEntitlementResponse(BaseModel):
    user_id: str
    plan_id: str
    status: SubscriptionStatus
    source: SubscriptionSource
    product_id: str | None = None
    original_transaction_id: str | None = None
    renews_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubscriptionEntitlementUpsertRequest(BaseModel):
    plan_id: str
    status: SubscriptionStatus = SubscriptionStatus.active
    source: SubscriptionSource = SubscriptionSource.manual
    product_id: str | None = None
    original_transaction_id: str | None = None
    renews_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoreKitWebhookRequest(BaseModel):
    event_id: str | None = None
    user_id: str
    product_id: str
    status: SubscriptionStatus = SubscriptionStatus.active
    renews_at: datetime | None = None
    expires_at: datetime | None = None
    original_transaction_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GooglePlayWebhookRequest(BaseModel):
    event_id: str | None = None
    user_id: str
    product_id: str
    status: SubscriptionStatus = SubscriptionStatus.active
    renews_at: datetime | None = None
    expires_at: datetime | None = None
    original_transaction_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebhookProcessResponse(BaseModel):
    event_id: str
    processed: bool
    message: str


class CreditResetScheduleResponse(BaseModel):
    enabled: bool
    reset_hour_utc: int
    reset_minute_utc: int
    free_daily_credits: int
    pro_daily_credits: int
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class CreditResetScheduleUpdateRequest(BaseModel):
    enabled: bool | None = None
    reset_hour_utc: int | None = Field(default=None, ge=0, le=23)
    reset_minute_utc: int | None = Field(default=None, ge=0, le=59)
    free_daily_credits: int | None = Field(default=None, ge=0)
    pro_daily_credits: int | None = Field(default=None, ge=0)


class CreditResetRunResponse(BaseModel):
    started_at: datetime
    completed_at: datetime
    dry_run: bool
    users_processed: int
    balances_updated: int


class CreditResetTickResponse(BaseModel):
    checked_at: datetime
    due: bool
    ran: bool
    skipped_reason: str | None = None
    run_result: CreditResetRunResponse | None = None
