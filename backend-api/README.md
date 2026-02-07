# Backend API (Provider-flexible)

Backend scaffold for AI interior generation with:
- dashboard-controlled provider routing,
- plans/variables controls,
- analytics endpoints,
- database-backed persistence.

## Run locally

```bash
cd backend-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment variables

- `DATABASE_URL`: defaults to `sqlite:///./app.db`.
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
- `STOREKIT_WEBHOOK_SECRET`: optional shared secret for `/v1/webhooks/storekit`.
- `GOOGLE_PLAY_WEBHOOK_SECRET`: optional shared secret for `/v1/webhooks/google-play`.

## Key endpoints

### Mobile config bootstrap

- `GET /v1/config/bootstrap`
- `GET /v1/projects/board/{user_id}`
- `GET /v1/discover/feed?tab=Home`

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
- `GET /v1/admin/subscriptions/entitlements`
- `POST /v1/webhooks/storekit`
- `POST /v1/webhooks/google-play`

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
- `GET /v1/admin/providers/health`

## Notes

- `fal` provider is wired to queue endpoints; missing API key causes dispatch fallback/failure.
- `openai` provider supports live mode with `OPENAI_API_KEY`; otherwise it can return stubbed outputs for local development.
- OpenAI responses with `b64_json` are uploaded to configured S3-compatible storage and returned as public URLs.
- SQLAlchemy models are initialized on app startup.
- For scheduled daily reset, run `python scripts/run_credit_reset_tick.py` from `backend-api` via cron/worker.
