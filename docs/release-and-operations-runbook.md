# Release and Operations Runbook

This runbook defines how to ship and operate the universal HomeAI stack:
- backend API,
- web app,
- admin dashboard,
- iOS app,
- Android app.

## 1) Local preflight

Run full preflight from repository root:

```bash
./scripts/release_preflight.sh
```

Optional skips:

```bash
SKIP_IOS=1 ./scripts/release_preflight.sh
SKIP_ANDROID=1 ./scripts/release_preflight.sh
SKIP_API_SMOKE=1 ./scripts/release_preflight.sh
```

## 2) CI release gate

Use GitHub Actions workflow:
- `Release Readiness` (manual dispatch or on release tag `v*`).

Gate passes only when backend/web/admin/iOS/Android checks are all green.

## 3) Backend container release

Workflow:
- `Backend Image` builds/publishes `ghcr.io/<owner>/homeai-backend`.

Local build:

```bash
cd backend-api
docker build -t homeai-backend:local .
docker run --rm -p 8000:8000 --env-file ../deploy/backend-api.env.staging.example homeai-backend:local
```

## 4) Server deployment (template)

Files:
- `deploy/docker-compose.production-template.yml`
- `deploy/Caddyfile.template`
- `deploy/backend-api.env.production.example`

Typical steps:
1. Copy templates to target server.
2. Fill `backend-api.env` with production secrets.
   Use PostgreSQL in production via `postgresql+psycopg://...` `DATABASE_URL`.
3. Replace Caddy domain placeholders.
4. Pull latest backend image and run compose.
5. Verify `/healthz` and key API paths.

## 5) Web + admin deployment

Current approach:
- Static build output from:
  - `web-app/dist`
  - `admin-dashboard/dist`

Deploy target options:
- Vercel
- Netlify
- S3 + CloudFront

Requirements:
- Backend CORS must include web/admin domains.
- UI API base URL must point to production API.

## 6) Mobile release flow

### iOS
1. Generate project (`xcodegen generate`).
2. Archive and upload from Xcode or CI runner.
3. Submit to TestFlight first, then App Store production.
4. Verify webhook configuration receives StoreKit events.

### Android
1. Build release bundle (`./gradlew bundleRelease`).
2. Upload to Google Play internal testing first.
3. Promote to production after entitlement checks.
4. Verify webhook configuration receives Google Play events.

## 7) Billing and entitlement operations

Validate after each release:
- Web checkout success -> entitlement active.
- StoreKit event -> entitlement update.
- Google Play event -> entitlement update.

Reconciliation safety checks:
- conflicting source events preserve strongest active entitlement.
- duplicate webhook events are idempotent.

## 8) Experiment rollout operations

Seed template experiments:

```bash
cd backend-api
source .venv/bin/activate
python3 scripts/seed_experiment_templates.py
```

Daily automation (dry-run recommended first):

```bash
python3 scripts/run_experiment_automation.py --dry-run --hours 24 --rollout-limit 200
```

Operational details:
- `docs/experiment-automation-operations.md`

## 9) Post-release monitoring window (first 24h)

Monitor every 15-30 minutes:
- render success rate
- p95 latency
- queued jobs
- avg cost per render
- checkout conversion
- entitlement activation by source (`ios`, `android`, `web`)

If guardrail breach persists for 2 consecutive checks:
1. freeze rollout,
2. revert related provider/plan variable changes,
3. trigger incident response and rollback if needed.
