# Admin Activation Playbook (Site + iOS + Android)

This document is the operations guide for activating HomeAI in production and keeping web, iOS, and Android healthy after launch.

Use this together with:
- `docs/launch-readiness-checklist.md`
- `docs/release-and-operations-runbook.md`
- `docs/github-production-setup.md`

## 1) What “Active” means

A platform is considered active only when all of these are true:
- Backend API is up in production mode and secured.
- Web app is reachable from public domain and can complete login + render flow.
- Admin dashboard is reachable and can load analytics + provider settings.
- iOS app is available to target users (TestFlight or App Store production).
- Android app is available to target users (internal/closed/prod track).
- Subscription webhooks update entitlements correctly for web, iOS, and Android.
- Monitoring data is visible in admin analytics/health endpoints.

## 2) Ownership

- Product Owner: approves go-live and rollback decisions.
- Backend Owner: API, DB, secrets, webhooks.
- Web Owner: web-app deployment and domain.
- Mobile Owner: App Store Connect + Google Play rollout.
- Ops Owner: admin dashboard checks, analytics checks, incident response.

## 3) Activation Order (Do Not Reorder)

1. Backend production config + deploy.
2. Admin access/security verification.
3. Provider settings and product configs publish.
4. Webhooks verification.
5. Web + Admin deployment.
6. iOS + Android rollout.
7. End-to-end smoke checks.
8. First 24h monitoring window.

## 4) Backend Activation

1. Set production env values (minimum):
   - `APP_ENV=production`
   - `DATABASE_URL` (PostgreSQL recommended)
   - `ALLOWED_ORIGINS` (web/admin domains)
   - `ADMIN_API_TOKEN` and/or `ADMIN_USER_IDS`
   - `STOREKIT_WEBHOOK_SECRET`
   - `GOOGLE_PLAY_WEBHOOK_SECRET`
   - `WEB_BILLING_WEBHOOK_SECRET`
   - provider keys (`FAL_API_KEY`, optional `OPENAI_API_KEY`)
2. Ensure `ALLOW_OPEN_ADMIN_MODE` is unset in production.
3. Deploy backend and verify:
   - `GET /healthz`
   - `GET /v1/admin/analytics/dashboard?hours=24`
   - `GET /v1/admin/providers/health?hours=24`
4. Run release gate:
   - `./scripts/release_preflight.sh`

## 5) Admin Dashboard Activation Tasks

Open admin dashboard and execute this sequence:

1. `Setup` group:
   - Configure API Base URL.
   - Configure Bearer and/or Admin Token.
   - Test health.
2. `AI Routing` group:
   - Load published provider settings.
   - Validate enabled providers/fallback chain.
   - Validate preview/final model mapping.
   - Save draft changes only if needed.
   - Publish draft with actor/reason.
3. `Monetization` group:
   - Validate plans (`free`, `pro`, any regional variants).
   - Validate variable flags:
     - `preview_before_final_required`
     - daily credit/usage controls
     - experiment guardrail thresholds
4. `Experiments` group:
   - Ensure risky experiments are not active at launch.
   - Run guardrails in dry-run first.
   - Enable live automation only when metrics are stable.
5. `Reliability` group:
   - Validate credit reset schedule.
   - Validate provider health values are populated.
6. `Audit` group:
   - Confirm product/provider audit entries exist for all launch changes.

## 6) Web Activation

1. Vercel project root must point to repository root.
2. Deploy latest `main`.
3. Verify:
   - `/` resolves and opens web app.
   - `/web-app/index.html` loads correctly.
   - Login works.
   - Create flow works (photo -> room -> style -> generate).
   - Custom style creation works (name + prompt + thumbnail).
4. Confirm backend CORS includes the deployed web origin.

## 7) iOS Activation

1. Build and archive release.
2. Upload to App Store Connect.
3. Start with TestFlight external/internal validation.
4. Verify:
   - auth/login
   - render preview + final
   - purchase/restore
   - entitlement sync after webhook
5. Promote to App Store production by staged rollout.

## 8) Android Activation

1. Build release AAB (`bundleRelease`).
2. Upload to Google Play internal track first.
3. Verify same critical flows as iOS.
4. Promote internal -> closed -> production staged rollout.
5. Monitor crash/ANR and conversion before increasing rollout.

## 9) Subscription/Webhook Verification

Run one test purchase path per platform:
- Web checkout -> entitlement active (`source=web`)
- iOS purchase -> entitlement active (`source=ios`)
- Android purchase -> entitlement active (`source=android`)

Then validate no unintended downgrade:
- If active entitlement exists, non-active webhook from another source should not incorrectly downgrade.

## 10) Go-Live Sign-Off Checklist

- Backend healthy, secured, and serving production DB.
- Admin dashboard connected and showing analytics.
- Provider settings published and audited.
- Plans/variables verified.
- Webhooks verified for all 3 sources.
- Web production URL validated by non-admin test user.
- iOS rollout approved (TestFlight/prod as planned).
- Android rollout approved (track progression as planned).
- Incident owner + rollback owner assigned.

## 11) Rollback Rules (Fast)

If severe issue occurs:

1. AI/provider issue:
   - Use admin provider rollback to previous version.
2. Pricing/plan issue:
   - Revert plan/variable changes in admin dashboard.
3. Experiment issue:
   - pause experiment or run guardrail enforcement.
4. Web deployment issue:
   - rollback Vercel deployment to previous stable version.
5. Backend issue:
   - rollback container/image release and restore last stable config.

Always record rollback reason in audit fields (`actor`, `reason`).

## 12) First 24 Hours Operations

Cadence:
- First 2h: check every 15 min.
- Next 6h: check hourly.
- Next 16h: check every 2-4h.

Watch:
- render success rate
- p95 latency
- queue backlog
- paid conversion
- webhook failures
- mobile crash/ANR

If any threshold breaks, pause rollouts and execute rollback rule set.

## 13) Weekly Operations (After Launch)

- Review provider cost/performance and adjust routing.
- Review plan conversion and churn indicators.
- Review experiment outcomes, keep winners, archive losers.
- Review audit logs for unauthorized/high-risk changes.
- Confirm credit reset schedule and entitlement reconciliations are healthy.

---

If you need a single “launch button” process, convert this document into an internal checklist run where each section has a named owner and timestamped sign-off.
