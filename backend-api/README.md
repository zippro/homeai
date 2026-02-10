# Backend API (Provider-flexible)

Backend scaffold for AI interior generation with:
- dashboard-controlled provider routing,
- plans/variables controls,
- analytics endpoints,
- database-backed persistence.

## Run locally

```bash
cd backend-api
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Quality commands:
```bash
make quality
```

Smoke flow against a running local API:
```bash
python3 scripts/smoke_api_flow.py
python3 scripts/smoke_entitlement_reconciliation.py
python3 scripts/run_experiment_guardrails.py --dry-run --hours 24
python3 scripts/run_experiment_automation.py --dry-run --hours 24 --rollout-limit 200
python3 scripts/seed_experiment_templates.py
# Optional: webhook notification + strict exit behavior
python3 scripts/run_experiment_automation.py --hours 24 --rollout-limit 200 --notify-webhook-url https://hooks.example.com/homeai --fail-on-breach --fail-on-rollout-blocked
```

Operational deployment examples: see `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/experiment-automation-operations.md`.
Release runbook: `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/release-and-operations-runbook.md`.

## Container build

Build:
```bash
cd backend-api
docker build -t homeai-backend:local .
```

Run:
```bash
docker run --rm -p 8000:8000 --env-file .env homeai-backend:local
```

## Environment variables

- `DATABASE_URL`: defaults to `sqlite:///./app.db`.
  PostgreSQL is supported via URLs like `postgresql+psycopg://user:pass@host:5432/dbname`.
- `ALLOWED_ORIGINS`: defaults to `*`; comma-separated list for CORS (for example `https://admin.yourdomain.com,http://localhost:4173`).
- `APP_ENV`: defaults to non-production if unset. Use `production` (or `prod`) in live environments.
- `FAL_API_KEY`: required for live fal.ai queue calls.
- `FAL_QUEUE_BASE`: defaults to `https://queue.fal.run`.
- `FAL_TIMEOUT_SECONDS`: defaults to `45`.
- `OPENAI_API_KEY`: optional, enables live OpenAI image calls.
- `OPENAI_API_BASE`: defaults to `https://api.openai.com/v1`.
- `OPENAI_STUB_IF_MISSING_KEY`: defaults to `true` for local stub fallback.
- `STORAGE_BUCKET`: required for uploading OpenAI `b64_json` outputs.
- `STORAGE_REGION`: defaults to `us-east-1`.
- `STORAGE_ENDPOINT_URL`: optional, for S3-compatible providers (R2/MinIO/etc.).
- `STORAGE_ACCESS_KEY_ID`: optional if runtime has IAM role.
- `STORAGE_SECRET_ACCESS_KEY`: optional if runtime has IAM role.
- `STORAGE_PUBLIC_BASE_URL`: optional CDN/public URL base for returned image URLs.
- `STOREKIT_WEBHOOK_SECRET`: shared secret for `/v1/webhooks/storekit` (required in production).
- `GOOGLE_PLAY_WEBHOOK_SECRET`: shared secret for `/v1/webhooks/google-play` (required in production).
- `WEB_BILLING_WEBHOOK_SECRET`: shared secret for `/v1/webhooks/web-billing` (required in production).
- `WEB_BILLING_CHECKOUT_BASE_URL`: optional base URL for generated web checkout session links.
- `ADMIN_API_TOKEN`: optional static token for admin endpoints via `X-Admin-Token`.
- `ADMIN_USER_IDS`: optional comma-separated user IDs allowed on admin endpoints via bearer auth.
- `ALLOW_OPEN_ADMIN_MODE`: optional override (`true`) to allow admin endpoints without token/user config in production. Keep unset in production unless you intentionally need temporary bootstrap access.
- `EXPERIMENT_AUTOMATION_NOTIFY_WEBHOOK_URL`: optional webhook URL used by `run_experiment_automation.py`.

## Key endpoints

### Authentication

- `POST /v1/auth/login-dev`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`

### Mobile config bootstrap

- `GET /v1/config/bootstrap`
- `GET /v1/session/bootstrap/me?board_limit=30&experiment_limit=50`
- `GET /v1/projects/board/{user_id}`
- `GET /v1/projects/board/me`
- `GET /v1/discover/feed?tab=Home`
- `GET /v1/profile/overview/{user_id}`
- `GET /v1/profile/overview/me`

### AI generation

- `GET /v1/ai/providers`
- `POST /v1/ai/render-jobs`
- `GET /v1/ai/render-jobs/{job_id}`
- `POST /v1/ai/render-jobs/{job_id}/cancel`

### Credits

- `GET /v1/credits/balance/{user_id}`
- `POST /v1/credits/consume`
- `POST /v1/credits/grant`

### Credit reset controls

- `GET /v1/admin/credits/reset-schedule`
- `PUT /v1/admin/credits/reset-schedule`
- `POST /v1/admin/credits/run-daily-reset`
- `POST /v1/admin/credits/tick-reset`

### Subscriptions and webhooks

- `GET /v1/subscriptions/entitlements/{user_id}`
- `PUT /v1/subscriptions/entitlements/{user_id}`
- `GET /v1/subscriptions/catalog`
- `POST /v1/subscriptions/web/checkout-session`
- `GET /v1/admin/subscriptions/entitlements`
- `POST /v1/webhooks/storekit`
- `POST /v1/webhooks/google-play`
- `POST /v1/webhooks/web-billing`

### Experiments (A/B testing)

- `POST /v1/experiments/assign`
- `GET /v1/experiments/active/{user_id}`
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

### Provider dashboard controls

- `GET /v1/admin/provider-settings`
- `GET /v1/admin/provider-settings/draft`
- `PUT /v1/admin/provider-settings/draft`
- `POST /v1/admin/provider-settings/publish`
- `POST /v1/admin/provider-settings/rollback/{version}`
- `GET /v1/admin/provider-settings/versions`
- `GET /v1/admin/provider-settings/audit`

### Plans and variables dashboard controls

- `GET /v1/admin/plans`
- `PUT /v1/admin/plans/{plan_id}`
- `DELETE /v1/admin/plans/{plan_id}`
- `GET /v1/admin/variables`
- `PUT /v1/admin/variables/{key}`
- `DELETE /v1/admin/variables/{key}`
- `GET /v1/admin/product-audit`

### Analytics

- `POST /v1/analytics/events`
- `GET /v1/admin/analytics/overview`
- `GET /v1/admin/analytics/dashboard?hours=24`
- `GET /v1/admin/providers/health`

`/v1/admin/analytics/dashboard` includes render health KPIs, queue metrics, subscription source mix, conversion funnel metrics, and experiment variant performance.

## Notes

- `fal` provider is wired to queue endpoints; missing API key causes dispatch fallback/failure.
- `openai` provider supports live mode with `OPENAI_API_KEY`; otherwise it can return stubbed outputs for local development.
- OpenAI responses with `b64_json` are uploaded to configured S3-compatible storage and returned as public URLs.
- Render credits are calculated from the user effective plan (`preview_cost_credits`/`final_cost_credits`) instead of hardcoded values.
- Final render can be blocked by `preview_before_final_required` if there is no completed preview in the same project/style.
- User-scoped endpoints require `Authorization: Bearer <token>` from `/v1/auth/login-dev`.
- SQLAlchemy models are initialized on app startup.
- For scheduled daily reset, run `python scripts/run_credit_reset_tick.py` from `backend-api` via cron/worker.
- Admin endpoints auth modes:
  - open mode (default in non-production): if `ADMIN_API_TOKEN` and `ADMIN_USER_IDS` are both unset,
  - production-safe default: with `APP_ENV=production`, unset admin credentials return `401 admin_auth_not_configured`,
  - production override: set `ALLOW_OPEN_ADMIN_MODE=true` only for temporary bootstrap access,
  - token mode: set `ADMIN_API_TOKEN` and send `X-Admin-Token`,
  - role mode: set `ADMIN_USER_IDS` and send bearer token for an allowed user.
- Webhook auth behavior:
  - non-production: webhook routes accept missing secrets (for local/dev smoke flows),
  - production (`APP_ENV=production`): webhook routes require configured matching secrets.
- Webhook entitlement reconciliation policy:
  - keep `active` entitlement if a later webhook reports non-active status from another source,
  - if both entitlements are `active`, keep the higher-priced plan,
  - if plan price is tied, keep the one with later renewal/expiry horizon.
- Experiment guardrail enforcement:
  - `POST /v1/admin/experiments/guardrails/evaluate` checks each experiment against configured guardrails,
  - default pause behavior requires `2` consecutive breached runs before auto-pause,
  - override streak threshold via variable `experiment_guardrail_consecutive_runs_required`.
- Experiment performance evaluator:
  - `GET /v1/admin/experiments/{experiment_id}/performance` returns variant-level conversion/quality/cost metrics,
  - includes paid conversion source breakdown (`web`/`ios`/`android`) per variant,
  - computes lift vs control and two-sided p-value for the configured primary metric,
  - recommendation tuning variables:
    - `experiment_significance_alpha` (default `0.05`)
    - `experiment_primary_metric_min_sample_size` (default `100`).
- Experiment auto rollout:
  - `POST /v1/admin/experiments/{experiment_id}/rollout/evaluate` evaluates winner + guardrails and steps rollout,
  - rollout ladder is `10% -> 50% -> 100%`,

- Experiment trend explorer:
  - `GET /v1/admin/experiments/{experiment_id}/trends?hours=...&bucket_hours=...` returns bucketed points per variant,
  - each bucket includes quality/cost/funnel metrics and primary metric value to inspect drift before rollout.
- Experiment automation runner:
  - `POST /v1/admin/experiments/automation/run` executes guardrails and bulk rollout in one run,
  - supports `dry_run=true` for simulation or `dry_run=false` for live enforcement.
  - automation runs are recorded in audit logs and exposed via `GET /v1/admin/experiments/automation/history`.
