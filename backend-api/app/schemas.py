from __future__ import annotations

from datetime import datetime
from app.time_utils import utc_now
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
    created_at: datetime = Field(default_factory=utc_now)
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
    web_product_id: str | None = None
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
    web_product_id: str | None = None
    features: list[str] = Field(default_factory=list)


class AppVariable(BaseModel):
    key: str
    value: ScalarValue
    description: str | None = None


class VariableUpsertRequest(BaseModel):
    value: ScalarValue
    description: str | None = None


class ExperimentVariant(BaseModel):
    variant_id: str
    weight: int = Field(default=50, ge=1)
    config: dict[str, ScalarValue] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    experiment_id: str
    name: str
    description: str | None = None
    is_active: bool = True
    assignment_unit: str = "user_id"
    primary_metric: str
    guardrails: dict[str, ScalarValue] = Field(default_factory=dict)
    variants: list[ExperimentVariant] = Field(default_factory=list)
    rollout_state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ExperimentUpsertRequest(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    assignment_unit: str = "user_id"
    primary_metric: str
    guardrails: dict[str, ScalarValue] = Field(default_factory=dict)
    variants: list[ExperimentVariant] = Field(default_factory=list)


class ExperimentTemplate(BaseModel):
    template_id: str
    name: str
    description: str | None = None
    assignment_unit: str = "user_id"
    primary_metric: str
    guardrails: dict[str, ScalarValue] = Field(default_factory=dict)
    variants: list[ExperimentVariant] = Field(default_factory=list)


class ExperimentAssignRequest(BaseModel):
    experiment_id: str
    user_id: str


class ExperimentAssignResponse(BaseModel):
    experiment_id: str
    user_id: str
    variant_id: str
    config: dict[str, ScalarValue] = Field(default_factory=dict)
    assigned_at: datetime
    from_cache: bool = False


class ActiveExperimentAssignmentsResponse(BaseModel):
    user_id: str
    assignments: list[ExperimentAssignResponse] = Field(default_factory=list)


class ExperimentGuardrailBreach(BaseModel):
    metric_key: str
    operator: str
    threshold: float
    actual: float | None = None
    message: str


class ExperimentGuardrailEvaluation(BaseModel):
    experiment_id: str
    name: str
    is_active: bool
    breached: bool
    paused: bool
    violation_streak: int = 0
    required_streak: int = 2
    skipped: bool = False
    skipped_reason: str | None = None
    breach_count: int
    guardrails: dict[str, ScalarValue] = Field(default_factory=dict)
    breaches: list[ExperimentGuardrailBreach] = Field(default_factory=list)


class ExperimentGuardrailRunResponse(BaseModel):
    checked_at: datetime
    window_hours: int
    dry_run: bool
    required_streak: int = 2
    evaluated_count: int
    breached_count: int
    paused_count: int
    evaluations: list[ExperimentGuardrailEvaluation] = Field(default_factory=list)


class ExperimentPerformanceVariant(BaseModel):
    variant_id: str
    assigned_users: int
    active_paid_users: int
    paid_conversion_rate: float
    checkout_started_users: int
    checkout_start_rate: float
    preview_users: int
    final_users: int
    preview_to_final_rate: float
    render_events: int
    render_success_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_cost_usd: float
    avg_cost_usd: float | None
    primary_metric_value: float
    paid_source_breakdown: dict[str, int] = Field(default_factory=dict)
    primary_metric_successes: int | None = None
    primary_metric_trials: int | None = None
    lift_vs_control_pct: float | None = None
    p_value: float | None = None
    statistically_significant: bool = False


class ExperimentPerformanceResponse(BaseModel):
    experiment_id: str
    name: str
    primary_metric: str
    generated_at: datetime
    window_hours: int
    control_variant_id: str | None = None
    significance_alpha: float
    minimum_sample_size: int
    total_assigned_users: int
    recommended_variant_id: str | None = None
    recommendation_reason: str
    variants: list[ExperimentPerformanceVariant] = Field(default_factory=list)


class ExperimentRolloutEvaluationResponse(BaseModel):
    experiment_id: str
    checked_at: datetime
    dry_run: bool
    window_hours: int
    winner_variant_id: str | None = None
    recommendation_reason: str
    guardrails_clear: bool
    blocked_reason: str | None = None
    current_rollout_percent: int
    next_rollout_percent: int
    rollout_status: str
    applied: bool = False
    performance_total_assigned_users: int
    minimum_sample_size: int
    significance_alpha: float


class ExperimentBulkRolloutEvaluationResponse(BaseModel):
    checked_at: datetime
    dry_run: bool
    window_hours: int
    evaluated_count: int
    applied_count: int
    blocked_count: int
    results: list[ExperimentRolloutEvaluationResponse] = Field(default_factory=list)


class ExperimentAutomationRunResponse(BaseModel):
    checked_at: datetime
    dry_run: bool
    window_hours: int
    rollout_limit: int
    guardrails: ExperimentGuardrailRunResponse
    rollouts: ExperimentBulkRolloutEvaluationResponse


class ExperimentTrendPoint(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    assigned_users: int
    render_events: int
    render_success_rate: float
    avg_latency_ms: float | None
    total_cost_usd: float
    preview_users: int
    final_users: int
    preview_to_final_rate: float
    checkout_started_users: int
    paid_activations: int
    paid_activation_rate: float
    primary_metric_value: float


class ExperimentVariantTrend(BaseModel):
    variant_id: str
    points: list[ExperimentTrendPoint] = Field(default_factory=list)


class ExperimentTrendResponse(BaseModel):
    experiment_id: str
    name: str
    primary_metric: str
    generated_at: datetime
    window_hours: int
    bucket_hours: int
    control_variant_id: str | None = None
    variants: list[ExperimentVariantTrend] = Field(default_factory=list)


class AnalyticsEventRequest(BaseModel):
    event_name: str
    user_id: str | None = None
    platform: str | None = None
    provider: str | None = None
    operation: OperationType | None = None
    status: JobStatus | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    occurred_at: datetime = Field(default_factory=utc_now)


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


class AnalyticsDashboardSummary(BaseModel):
    window_hours: int
    total_events: int
    unique_users: int
    active_render_users: int
    render_events: int
    render_success: int
    render_failed: int
    render_in_progress: int
    render_success_rate: float
    preview_completed: int
    final_completed: int
    preview_to_final_rate: float
    avg_latency_ms: float | None
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    total_cost_usd: float
    avg_cost_per_render_usd: float | None


class AnalyticsProviderMetric(BaseModel):
    provider: str
    total_events: int
    success_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_cost_usd: float
    avg_cost_usd: float | None


class AnalyticsOperationMetric(BaseModel):
    operation: str
    total_events: int
    success_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_cost_usd: float
    avg_cost_usd: float | None


class AnalyticsPlatformMetric(BaseModel):
    platform: str
    total_events: int
    render_events: int
    render_success: int
    render_success_rate: float


class AnalyticsStatusMetric(BaseModel):
    status: str
    count: int


class AnalyticsCreditReasonMetric(BaseModel):
    reason: str
    events: int
    net_delta: int
    absolute_delta: int


class AnalyticsCreditsMetrics(BaseModel):
    consumed_total: int
    granted_total: int
    refunded_total: int
    daily_reset_total: int
    unique_consumers: int
    top_reasons: list[AnalyticsCreditReasonMetric] = Field(default_factory=list)


class AnalyticsSubscriptionMetrics(BaseModel):
    active_subscriptions: int
    active_by_plan: dict[str, int]
    renewals_due_7d: int
    expirations_due_7d: int


class AnalyticsQueueMetrics(BaseModel):
    queued_jobs: int
    in_progress_jobs: int
    completed_jobs_window: int
    failed_jobs_window: int
    canceled_jobs_window: int


class AnalyticsFunnelMetrics(BaseModel):
    login_users: int
    preview_users: int
    final_users: int
    checkout_starts: int
    paid_activations: int
    login_to_preview_rate: float
    preview_to_final_rate: float
    final_to_checkout_rate: float
    checkout_to_paid_rate: float


class AnalyticsSubscriptionSourceMetric(BaseModel):
    source: str
    active_subscriptions: int
    active_share_pct: float


class AnalyticsExperimentVariantMetric(BaseModel):
    variant_id: str
    assigned_users: int
    active_paid_users: int
    paid_conversion_rate: float


class AnalyticsExperimentMetric(BaseModel):
    experiment_id: str
    name: str
    primary_metric: str
    is_active: bool
    total_assigned_users: int
    active_paid_users: int
    paid_conversion_rate: float
    variants: list[AnalyticsExperimentVariantMetric] = Field(default_factory=list)


class AnalyticsAlert(BaseModel):
    code: str
    severity: str
    message: str
    current_value: float | int | None = None
    threshold: float | int | None = None


class AnalyticsDashboardResponse(BaseModel):
    generated_at: datetime
    summary: AnalyticsDashboardSummary
    provider_breakdown: list[AnalyticsProviderMetric]
    operation_breakdown: list[AnalyticsOperationMetric]
    platform_breakdown: list[AnalyticsPlatformMetric]
    status_breakdown: list[AnalyticsStatusMetric]
    credits: AnalyticsCreditsMetrics
    subscriptions: AnalyticsSubscriptionMetrics
    subscription_sources: list[AnalyticsSubscriptionSourceMetric]
    queue: AnalyticsQueueMetrics
    funnel: AnalyticsFunnelMetrics
    experiment_breakdown: list[AnalyticsExperimentMetric]
    alerts: list[AnalyticsAlert]


class RenderJobCreateRequest(BaseModel):
    user_id: str | None = None
    platform: str | None = None
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
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
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
    web = "web"
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


class ProfileOverviewResponse(BaseModel):
    user_id: str
    credits: CreditBalanceResponse
    entitlement: SubscriptionEntitlementResponse
    effective_plan: PlanConfig
    next_credit_reset_at: datetime | None = None


class DevLoginRequest(BaseModel):
    user_id: str
    platform: str | None = None
    ttl_hours: int = Field(default=24 * 30, ge=1, le=24 * 90)


class AuthSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    expires_at: datetime


class AuthMeResponse(BaseModel):
    user_id: str
    platform: str | None = None
    expires_at: datetime


class SessionBootstrapResponse(BaseModel):
    me: AuthMeResponse
    profile: ProfileOverviewResponse
    board: UserBoardResponse
    experiments: ActiveExperimentAssignmentsResponse
    catalog: list[PlanConfig]
    variables: dict[str, ScalarValue]
    provider_defaults: dict[str, Any]


class LogoutResponse(BaseModel):
    revoked: bool


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


class WebBillingWebhookRequest(BaseModel):
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


class WebCheckoutSessionRequest(BaseModel):
    user_id: str
    plan_id: str
    success_url: str
    cancel_url: str


class WebCheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    provider: str = "stripe"
