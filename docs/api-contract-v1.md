# API Contract v1 (Mobile + Dashboard)

## Base URL

- `https://api.yourdomain.com`

## Auth

Use bearer token for user-scoped APIs:
- `Authorization: Bearer <access_token>`

User-scoped endpoints include:
- `/v1/ai/render-jobs` when `user_id` is provided
- `/v1/projects/board/*`
- `/v1/profile/overview/*`
- `/v1/credits/*`
- `/v1/subscriptions/entitlements/*`

Dev login (for local/staging):
- `POST /v1/auth/login-dev`
```json
{
  "user_id": "user_001",
  "platform": "ios",
  "ttl_hours": 720
}
```

Response:
```json
{
  "access_token": "dev_xxx",
  "token_type": "bearer",
  "user_id": "user_001",
  "expires_at": "2026-03-01T12:00:00Z"
}
```

- `GET /v1/auth/me`
- `POST /v1/auth/logout`

## Admin access

Admin endpoints are under `/v1/admin/*` and support three runtime modes:
- open mode: `ADMIN_API_TOKEN` and `ADMIN_USER_IDS` unset,
- token mode: set `ADMIN_API_TOKEN` and send `X-Admin-Token: <token>`,
- role mode: set `ADMIN_USER_IDS` and send bearer token for an allowed user.

If both token and role modes are configured, either valid credential is accepted.

## 1) Provider control endpoints (Dashboard)

### Get published provider settings
- `GET /v1/admin/provider-settings`

### Get draft provider settings
- `GET /v1/admin/provider-settings/draft`

### Update draft provider settings
- `PUT /v1/admin/provider-settings/draft?actor=admin@company.com&reason=flux2_rollout`

Body example:
```json
{
  "default_provider": "fal",
  "enabled_providers": ["fal", "openai", "mock"],
  "fallback_chain": ["fal", "openai", "mock"],
  "provider_models": {
    "fal": {
      "preview_model": "fal-ai/flux-1/schnell",
      "final_model": "fal-ai/flux-2"
    },
    "openai": {
      "preview_model": "gpt-image-1-mini",
      "final_model": "gpt-image-1"
    },
    "mock": {
      "preview_model": "mock-preview",
      "final_model": "mock-final"
    }
  }
}
```

### Publish draft
- `POST /v1/admin/provider-settings/publish`

Body:
```json
{ "actor": "admin@company.com", "reason": "approved rollout" }
```

### Roll back to a previous version
- `POST /v1/admin/provider-settings/rollback/{version}`

Body:
```json
{ "actor": "admin@company.com", "reason": "latency regression" }
```

### Version history and audit
- `GET /v1/admin/provider-settings/versions`
- `GET /v1/admin/provider-settings/audit`

## Mobile bootstrap endpoint

- `GET /v1/config/bootstrap`
- `GET /v1/session/bootstrap/me?board_limit=30&experiment_limit=50`
- `GET /v1/projects/board/{user_id}?limit=30`
- `GET /v1/projects/board/me?limit=30`
- `GET /v1/discover/feed?tab=Home`
- `GET /v1/profile/overview/{user_id}`
- `GET /v1/profile/overview/me`

Response shape:
```json
{
  "active_plans": [
    {
      "plan_id": "free",
      "display_name": "Free",
      "is_active": true,
      "daily_credits": 3,
      "preview_cost_credits": 1,
      "final_cost_credits": 2,
      "monthly_price_usd": 0,
      "ios_product_id": null,
      "android_product_id": null,
      "web_product_id": null,
      "features": ["daily_free_credits", "preview_generation"]
    }
  ],
  "variables": {
    "daily_credit_limit_enabled": true,
    "preview_before_final_required": true
  },
  "provider_defaults": {
    "default_provider": "fal",
    "fallback_chain": ["fal", "openai"],
    "version": 2
  }
}
```

Unified authenticated bootstrap (`/v1/session/bootstrap/me`) response shape:
```json
{
  "me": {
    "user_id": "user_001",
    "platform": "ios",
    "expires_at": "2026-03-01T10:00:00Z"
  },
  "profile": {
    "user_id": "user_001",
    "credits": { "user_id": "user_001", "balance": 37 },
    "entitlement": {
      "user_id": "user_001",
      "plan_id": "pro",
      "status": "active",
      "source": "web"
    },
    "effective_plan": {
      "plan_id": "pro",
      "display_name": "Pro",
      "is_active": true,
      "daily_credits": 80,
      "preview_cost_credits": 1,
      "final_cost_credits": 1,
      "monthly_price_usd": 14.99,
      "ios_product_id": "pro_monthly_ios",
      "android_product_id": "pro_monthly_android",
      "web_product_id": "pro_monthly_web",
      "features": ["higher_limits", "priority_queue", "no_ads"]
    },
    "next_credit_reset_at": "2026-02-10T00:00:00Z"
  },
  "board": {
    "user_id": "user_001",
    "projects": []
  },
  "experiments": {
    "user_id": "user_001",
    "assignments": []
  },
  "catalog": [],
  "variables": {
    "daily_credit_limit_enabled": true
  },
  "provider_defaults": {
    "default_provider": "fal",
    "fallback_chain": ["fal", "openai"],
    "version": 2
  }
}
```

## Board endpoint

- `GET /v1/projects/board/{user_id}?limit=30`
- `GET /v1/projects/board/me?limit=30`

Response shape:
```json
{
  "user_id": "user_001",
  "projects": [
    {
      "project_id": "mobile_project",
      "cover_image_url": "https://cdn.example.com/source.jpg",
      "generation_count": 2,
      "last_job_id": "job_123",
      "last_style_id": "modern_minimal",
      "last_status": "completed",
      "last_output_url": "https://cdn.example.com/output.jpg",
      "last_updated_at": "2026-02-07T10:00:00Z"
    }
  ]
}
```

## Discover feed endpoint

- `GET /v1/discover/feed?tab=Home`

When `tab` is omitted, API returns all sections.

## 2) Plans and variables endpoints (Dashboard)

### Plans
- `GET /v1/admin/plans`
- `PUT /v1/admin/plans/{plan_id}`
- `DELETE /v1/admin/plans/{plan_id}`

Plan upsert body:
```json
{
  "display_name": "Pro",
  "is_active": true,
  "daily_credits": 100,
  "preview_cost_credits": 1,
  "final_cost_credits": 1,
  "monthly_price_usd": 14.99,
  "ios_product_id": "pro_monthly_ios",
  "android_product_id": "pro_monthly_android",
  "web_product_id": "pro_monthly_web",
  "features": ["priority_queue", "no_ads"]
}
```

### Variables
- `GET /v1/admin/variables`
- `PUT /v1/admin/variables/{key}`
- `DELETE /v1/admin/variables/{key}`

Variable upsert body:
```json
{
  "value": true,
  "description": "Enable daily limit gate"
}
```

### Product audit
- `GET /v1/admin/product-audit`

### Experiments (A/B tests)
- `GET /v1/admin/experiments`
- `GET /v1/admin/experiments/templates`
- `PUT /v1/admin/experiments/{experiment_id}`
- `DELETE /v1/admin/experiments/{experiment_id}`
- `GET /v1/admin/experiments/audit`
- `POST /v1/admin/experiments/guardrails/evaluate?hours=24&dry_run=true`
- `GET /v1/admin/experiments/{experiment_id}/performance?hours=168`
- `GET /v1/admin/experiments/{experiment_id}/trends?hours=168&bucket_hours=24`
- `POST /v1/admin/experiments/{experiment_id}/rollout/evaluate?hours=168&dry_run=true`
- `POST /v1/admin/experiments/rollout/evaluate-all?hours=168&dry_run=true&limit=200`
- `POST /v1/admin/experiments/automation/run?hours=168&dry_run=true&rollout_limit=200`
- `GET /v1/admin/experiments/automation/history?limit=50`
- `POST /v1/experiments/assign`
- `GET /v1/experiments/active/{user_id}`

Experiment upsert body:
```json
{
  "name": "Paywall Timing",
  "description": "On exhaustion vs after first preview",
  "is_active": true,
  "assignment_unit": "user_id",
  "primary_metric": "upgrade_conversion_7d",
  "guardrails": {
    "render_success_rate_min": 85,
    "p95_latency_max_ms": 12000
  },
  "variants": [
    {
      "variant_id": "control",
      "weight": 50,
      "config": {
        "paywall_mode": "on_exhaustion"
      }
    },
    {
      "variant_id": "treatment",
      "weight": 50,
      "config": {
        "paywall_mode": "after_first_preview"
      }
    }
  ]
}
```

Templates endpoint (`GET /v1/admin/experiments/templates`) returns reusable payload starters for common scenarios:
- pricing paywall timing,
- plan highlight,
- preview quality/cost,
- provider fallback order.

Guardrail evaluation response highlights:
- `evaluated_count`
- `breached_count`
- `paused_count`
- per experiment: `breached`, `paused`, `skipped`, `breaches[]`

`dry_run=true`: evaluates only, does not pause experiments.  
`dry_run=false`: pauses active experiments when configured guardrails are breached.

Performance evaluation response highlights:
- top-level: `control_variant_id`, `recommended_variant_id`, `recommendation_reason`
- variant-level:
  - `primary_metric_value`
  - `lift_vs_control_pct`
  - `p_value`
  - `statistically_significant`
  - `paid_source_breakdown` (active paid users by source: `web`, `ios`, `android`, etc.)
  - quality/cost metrics (`render_success_rate`, `avg_cost_usd`, latency)

Recommendation behavior:
- requires control and challenger sample size threshold (variable: `experiment_primary_metric_min_sample_size`)
- uses two-sided p-value threshold (variable: `experiment_significance_alpha`)
- ships only if challenger has positive, statistically significant lift.

Rollout evaluation response highlights:
- `current_rollout_percent`, `next_rollout_percent`
- `winner_variant_id`, `guardrails_clear`, `blocked_reason`
- `applied` (false for dry-run, true only when live run mutates rollout state)

Bulk rollout response highlights:
- `evaluated_count`, `applied_count`, `blocked_count`
- `results[]` with per-experiment rollout evaluation payload.

Automation response highlights:
- `guardrails`: guardrail run summary
- `rollouts`: bulk rollout summary
- `window_hours`, `dry_run`, `rollout_limit`

Automation history response highlights:
- list of audit entries (`action=experiment_automation_run`)
- metadata includes guardrail and rollout summary counts for each run.

Trend response highlights:
- top-level: `window_hours`, `bucket_hours`, `control_variant_id`
- variant-level: `points[]` bucket series with:
  - `assigned_users`
  - `primary_metric_value`
  - `render_success_rate`, `avg_latency_ms`, `total_cost_usd`
  - `preview_to_final_rate`, `paid_activation_rate`

## 3) Render endpoints (Mobile)

### Create render job
- `POST /v1/ai/render-jobs`

Body:
```json
{
  "user_id": "user_001",
  "platform": "ios",
  "project_id": "proj_123",
  "image_url": "https://cdn.example.com/original.jpg",
  "style_id": "modern_minimal",
  "operation": "restyle",
  "tier": "preview",
  "target_parts": ["full_room"],
  "mask_url": null,
  "prompt_overrides": {}
}
```

`platform` is optional but recommended (`ios`, `android`, `web`) so analytics can segment render performance by client surface.

If `user_id` is provided, backend auto-consumes credits using active plan pricing (`preview_cost_credits`, `final_cost_credits`) and returns `402 insufficient_credits` when balance is not enough. If provider dispatch fails before job creation, credits are auto-refunded.

If `preview_before_final_required=true` and no completed preview exists for the same `project_id` + `style_id`, final requests return `409 preview_required_before_final`.

Response includes selected provider/model and attempts used by fallback.

### Poll render job
- `GET /v1/ai/render-jobs/{job_id}`

### Cancel render job
- `POST /v1/ai/render-jobs/{job_id}/cancel`

### List registered providers
- `GET /v1/ai/providers`

## Credits endpoints

- `GET /v1/credits/balance/{user_id}`
- `POST /v1/credits/consume`
- `POST /v1/credits/grant`

Consume request:
```json
{
  "user_id": "user_001",
  "amount": 1,
  "reason": "render_preview",
  "idempotency_key": "render_job_abc_preview",
  "metadata": { "job_id": "abc" }
}
```

## Credit reset schedule endpoints (Admin)

- `GET /v1/admin/credits/reset-schedule`
- `PUT /v1/admin/credits/reset-schedule`
- `POST /v1/admin/credits/run-daily-reset?dry_run=true`
- `POST /v1/admin/credits/tick-reset`

Update schedule body:
```json
{
  "enabled": true,
  "reset_hour_utc": 0,
  "reset_minute_utc": 0,
  "free_daily_credits": 3,
  "pro_daily_credits": 80
}
```

`tick-reset` is intended for cron/worker execution and only runs a reset when schedule is enabled and due.

## Subscription endpoints

- `GET /v1/subscriptions/entitlements/{user_id}`
- `PUT /v1/subscriptions/entitlements/{user_id}`
- `GET /v1/subscriptions/catalog`
- `POST /v1/subscriptions/web/checkout-session`
- `GET /v1/admin/subscriptions/entitlements`

Upsert entitlement body:
```json
{
  "plan_id": "pro",
  "status": "active",
  "source": "manual",
  "product_id": "pro_monthly_ios",
  "original_transaction_id": "txn_001",
  "renews_at": "2026-03-01T12:00:00Z",
  "expires_at": null,
  "metadata": {
    "note": "manual support adjustment"
  }
}
```

Web checkout session request:
```json
{
  "user_id": "user_001",
  "plan_id": "pro",
  "success_url": "https://app.example.com/billing/success",
  "cancel_url": "https://app.example.com/billing/cancel"
}
```

Web checkout session response:
```json
{
  "session_id": "wcs_xxx",
  "checkout_url": "https://payments.example.com/checkout?...",
  "provider": "stripe"
}
```

## Webhook stub endpoints

- `POST /v1/webhooks/storekit`
- `POST /v1/webhooks/google-play`
- `POST /v1/webhooks/web-billing`

Reconciliation behavior across sources:
- `active` entitlement is not downgraded by a non-active webhook from another source.
- if multiple sources report `active`, backend keeps the higher-priced plan.
- when price is tied, backend keeps the entitlement with later renewal/expiry horizon.

Optional header:
- `X-Webhook-Secret: <shared-secret>`

StoreKit webhook body:
```json
{
  "event_id": "evt_storekit_1001",
  "user_id": "user_001",
  "product_id": "pro_monthly_ios",
  "status": "active",
  "renews_at": "2026-03-01T12:00:00Z",
  "expires_at": null,
  "original_transaction_id": "txn_001",
  "metadata": {
    "notification_type": "DID_RENEW"
  }
}
```

## Profile overview endpoint

- `GET /v1/profile/overview/{user_id}`
- `GET /v1/profile/overview/me`

Response shape:
```json
{
  "user_id": "user_001",
  "credits": {
    "user_id": "user_001",
    "balance": 12
  },
  "entitlement": {
    "user_id": "user_001",
    "plan_id": "pro",
    "status": "active",
    "source": "ios",
    "product_id": "pro_monthly_ios",
    "renews_at": "2026-03-01T12:00:00Z",
    "expires_at": null,
    "metadata": {}
  },
  "effective_plan": {
    "plan_id": "pro",
    "display_name": "Pro",
    "is_active": true,
    "daily_credits": 80,
    "preview_cost_credits": 1,
    "final_cost_credits": 1,
    "monthly_price_usd": 14.99,
    "ios_product_id": "pro_monthly_ios",
    "android_product_id": "pro_monthly_android",
    "features": ["higher_limits", "priority_queue", "no_ads"]
  },
  "next_credit_reset_at": "2026-02-08T00:00:00Z"
}
```

Google Play webhook body:
```json
{
  "event_id": "evt_gplay_2001",
  "user_id": "user_001",
  "product_id": "pro_monthly_android",
  "status": "active",
  "renews_at": "2026-03-01T12:00:00Z",
  "expires_at": null,
  "original_transaction_id": "g_txn_001",
  "metadata": {
    "notification_type": "SUBSCRIPTION_RENEWED"
  }
}
```

## 4) Analytics endpoints

### Ingest mobile/backend events
- `POST /v1/analytics/events`

Body:
```json
{
  "event_name": "render_status_updated",
  "user_id": "user_001",
  "platform": "ios",
  "provider": "fal",
  "operation": "restyle",
  "status": "completed",
  "latency_ms": 8340,
  "cost_usd": 0.04
}
```

### KPI overview for dashboard
- `GET /v1/admin/analytics/overview`

### Full analytics dashboard payload
- `GET /v1/admin/analytics/dashboard?hours=24`

Returns:
- summary KPIs (`render_success_rate`, latency, cost, preview->final conversion, active users)
- provider/operation/platform breakdowns
- status breakdown
- credits metrics
- subscription metrics + source mix (`ios/android/web/manual`)
- queue health metrics
- funnel metrics (`login -> preview -> final -> checkout -> paid`)
- experiment performance (`assigned users`, `paid conversion` by variant)
- generated alerts

Alert thresholds can be tuned from variables:
- `analytics_alert_min_success_rate_pct`
- `analytics_alert_max_p95_latency_ms`
- `analytics_alert_max_avg_cost_usd`
- `analytics_alert_max_queued_jobs`

### Provider health overview
- `GET /v1/admin/providers/health?hours=24`

## 5) UI mapping for mobile

- Tools tab calls `POST /v1/ai/render-jobs`.
- Create tab calls `GET /v1/ai/render-jobs/{job_id}` and project APIs.
- Discover tab uses separate content APIs (next phase).
- Profile tab calls plans/credits/subscription APIs (next phase).
