# Web-First Step-by-Step Plan (Then iOS + Android)

This sequence is the fastest path to launch with one shared backend and one shared product configuration.

## Phase 1: Lock the Web Baseline

1. Deploy backend API with production env and CORS for web/admin.
2. Deploy web app and admin dashboard to production URLs.
3. In admin dashboard:
   - configure provider settings,
   - seed default styles,
   - configure plans and variables,
   - verify route preview (provider/model),
   - publish provider draft.
4. Run end-to-end web smoke:
   - login,
   - create flow (image -> room -> style -> generate),
   - checkout start,
   - entitlement update,
   - board update.

Exit criteria:
- Web app can create preview/final renders with expected provider/model.
- Styles, plans, and prompts are editable from admin panel.

## Phase 2: Stabilize Operations

1. Turn on analytics dashboard monitoring (24h and 7d windows).
2. Configure provider health checks and queue alerts.
3. Run experiment guardrails in dry-run first.
4. Enable A/B experiments only after baseline is stable.

Exit criteria:
- Admin shows healthy metrics for success rate, latency, cost, and queue.
- Alert workflow is verified.

## Phase 3: Adapt Shared Contracts to Mobile

Use the same backend contracts on all clients:
- `/v1/session/bootstrap/me`
- `/v1/config/bootstrap`
- `/v1/styles`
- `/v1/ai/render-jobs`
- `/v1/subscriptions/*`

1. iOS and Android consume the same style catalog and plan catalog.
2. Keep prompt/style IDs centralized in admin (no hardcoded mobile-only catalogs).
3. Keep provider routing centralized in admin provider settings.

Exit criteria:
- iOS/Android display same style set and plan set as web.
- Render requests from mobile follow the same provider/model routes.

## Phase 4: Subscription and Entitlement Unification

1. Keep source-specific purchase flows:
   - web checkout,
   - App Store,
   - Google Play.
2. Normalize all entitlement writes into unified backend entitlement records.
3. Verify reconciliation for edge cases (renewal, cancellation, restore, downgrade protection).

Exit criteria:
- Same account sees correct plan on web + iOS + Android.
- No cross-platform entitlement regressions.

## Phase 5: Release Gates

Before each production release:

1. Backend tests:
   - route/config tests,
   - style catalog tests,
   - session bootstrap tests.
2. Frontend checks:
   - `web-app` build,
   - `admin-dashboard` build.
3. Android checks:
   - `./gradlew :app:assembleDebug :app:testDebugUnitTest`
4. Smoke scripts:
   - `scripts/smoke_api_flow.py`
   - `scripts/smoke_entitlement_reconciliation.py`

Exit criteria:
- All checks green.
- Release preflight passes.

## Phase 6: Launch Order

1. Web + admin public launch.
2. iOS TestFlight rollout.
3. Android internal/closed rollout.
4. Production staged rollout for mobile after health metrics are stable.

## Ongoing Weekly Loop

1. Update style catalog (thumbnail + prompt quality checks).
2. Review provider routing and cost/performance.
3. Review conversion experiments.
4. Audit plan/variable changes.
5. Review crashes, latency, and queue.
