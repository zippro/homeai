# Launch Readiness Checklist (Web + iOS + Android)

Use this checklist before each production release.

## 1) Source control + CI gates

- [ ] `main` is protected (no direct force push).
- [ ] Required checks enabled:
  - `Backend Quality`
  - `Web Admin Quality`
  - `Android Quality`
  - `iOS Quality`
  - `Release Readiness` (manual gate before release tag)
- [ ] Latest release commit is tagged (`vX.Y.Z`).

## 2) Backend production readiness

- [ ] Production env file created from `deploy/backend-api.env.production.example`.
- [ ] Provider keys set (`FAL_API_KEY`, optional `OPENAI_API_KEY`).
- [ ] Webhook secrets configured (`STOREKIT_WEBHOOK_SECRET`, `GOOGLE_PLAY_WEBHOOK_SECRET`, `WEB_BILLING_WEBHOOK_SECRET`).
- [ ] Admin auth configured (`ADMIN_API_TOKEN` and/or `ADMIN_USER_IDS`).
- [ ] CORS restricted (`ALLOWED_ORIGINS` not `*`).
- [ ] `/healthz` returns `{"status":"ok"}` in prod.

## 3) Web + admin release readiness

- [ ] Web app build succeeds (`web-app npm run build`).
- [ ] Admin dashboard build succeeds (`admin-dashboard npm run build`).
- [ ] API base URL points to production backend.
- [ ] Checkout success/cancel URLs configured correctly.

## 4) Mobile readiness

- [ ] iOS app builds with generated project (`xcodegen generate` then `xcodebuild`).
- [ ] Android app assembles in CI and local release mode.
- [ ] App config values use production API URL for release builds.
- [ ] Subscription product IDs match backend plans (`ios_product_id`, `android_product_id`, `web_product_id`).

## 5) Billing + entitlement verification

- [ ] Test web checkout end-to-end (checkout -> webhook -> entitlement active).
- [ ] Test StoreKit webhook event updates entitlement.
- [ ] Test Google Play webhook event updates entitlement.
- [ ] Reconciliation policy validated for conflicting webhook events.

## 6) Analytics + alerts

- [ ] Dashboard data present in `/v1/admin/analytics/dashboard`.
- [ ] Provider health populated in `/v1/admin/providers/health`.
- [ ] Alert thresholds reviewed:
  - `analytics_alert_min_success_rate_pct`
  - `analytics_alert_max_p95_latency_ms`
  - `analytics_alert_max_avg_cost_usd`
  - `analytics_alert_max_queued_jobs`

## 7) A/B testing operational readiness

- [ ] Experiment templates seeded (`seed_experiment_templates.py`).
- [ ] Guardrail automation dry-run passed.
- [ ] Rollout automation dry-run passed.
- [ ] Notification webhook configured for automation failures.

## 8) Final go/no-go

- [ ] `scripts/release_preflight.sh` passes (or all equivalent CI checks are green).
- [ ] No P0/P1 open issues for changed modules.
- [ ] Rollback owner assigned and rollback command documented.
- [ ] Release announcement + monitoring owner assigned.
