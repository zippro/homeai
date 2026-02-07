# API Contract v1 (Mobile + Dashboard)

## Base URL

- `https://api.yourdomain.com`

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
- `GET /v1/projects/board/{user_id}?limit=30`
- `GET /v1/discover/feed?tab=Home`

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

## Board endpoint

- `GET /v1/projects/board/{user_id}?limit=30`

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

## 3) Render endpoints (Mobile)

### Create render job
- `POST /v1/ai/render-jobs`

Body:
```json
{
  "user_id": "user_001",
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

If `user_id` is provided, backend will auto-consume credits (`preview=1`, `final=2`) and return `402 insufficient_credits` when balance is not enough. If provider dispatch fails before job creation, credits are auto-refunded.

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

## Webhook stub endpoints

- `POST /v1/webhooks/storekit`
- `POST /v1/webhooks/google-play`

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

### Provider health overview
- `GET /v1/admin/providers/health?hours=24`

## 5) UI mapping for mobile

- Tools tab calls `POST /v1/ai/render-jobs`.
- Create tab calls `GET /v1/ai/render-jobs/{job_id}` and project APIs.
- Discover tab uses separate content APIs (next phase).
- Profile tab calls plans/credits/subscription APIs (next phase).
