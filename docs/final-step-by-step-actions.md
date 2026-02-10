# Final Step-by-Step Actions (Do This Now)

Use this list from top to bottom without skipping.

## 1) Confirm latest code is live on GitHub

```bash
cd "/Users/narcadeteknolojiltd.sti./Documents/New project"
git checkout main
git pull origin main
git log --oneline -n 3
```

Expected top commit: `a3932cf` (or newer).

## 2) Verify local release gate once

```bash
./scripts/release_preflight.sh
```

Must finish with successful backend tests + web/admin checks + Android assembleDebug + iOS build-for-testing.

## 3) Deploy backend API to production

1. Set production environment variables on your backend host:
   - `APP_ENV=production`
   - `DATABASE_URL=...`
   - `ALLOWED_ORIGINS=https://<your-web-domain>,https://<your-admin-domain>`
   - `ADMIN_API_TOKEN=...`
   - `ALLOW_OPEN_ADMIN_MODE=false`
   - `FAL_API_KEY=...`
   - `OPENAI_API_KEY=...` (optional if you use OpenAI fallback)
   - `STOREKIT_WEBHOOK_SECRET=...`
   - `GOOGLE_PLAY_WEBHOOK_SECRET=...`
   - `WEB_BILLING_WEBHOOK_SECRET=...`
2. Deploy and verify:
   - `GET /healthz` returns `ok`.
   - `GET /v1/config/provider-route-preview` returns provider/model JSON.

## 4) Deploy web + admin on Vercel

1. Vercel project must point to repo root.
2. Deploy `main` branch.
3. Open:
   - `/web-app/index.html`
   - `/admin-dashboard/index.html`

## 5) First-time admin setup

In admin dashboard:

1. `API Settings`
   - Set production API URL.
   - Set Bearer token or `X-Admin-Token`.
   - Click `Test Health`.
2. `Provider Settings`
   - Load draft/published settings.
   - Confirm `default_provider`, `enabled_providers`, and fallback.
   - Verify `Model Route Preview`.
   - Publish draft.
3. `Style Catalog`
   - Click `Seed Example Styles`.
   - Confirm styles list is populated.
   - Use `Quick Template` + `Upsert Style` to edit prompts/thumbnails.
   - Check `Active Generator Route` block.
4. `Plans`
   - Verify `free` and `pro` prices/credits/product IDs.
5. `Variables`
   - Verify core flags (preview/final and credit controls).

## 6) End-user web smoke test

From `/web-app/index.html`:

1. Open Settings, set production API base URL.
2. Login with test user.
3. Complete create flow:
   - Step 1 image URL
   - Step 2 room
   - Step 3 style
   - Step 4 generate
4. Confirm output image is produced.
5. Confirm provider/model appears in Step 4 route preview.
6. Confirm board updates with generated project.

## 7) Subscription + entitlement verification

1. Web checkout test:
   - Start checkout from web profile.
   - Complete payment in test mode.
   - Verify entitlement becomes active.
2. iOS test purchase:
   - Verify backend entitlement source is `ios`.
3. Android test purchase:
   - Verify backend entitlement source is `android`.

## 8) Mobile rollout (after web is stable)

1. iOS:
   - Upload to TestFlight.
   - Validate login, render, purchase/restore.
2. Android:
   - Upload AAB to internal track.
   - Validate login, render, purchase.
3. Promote staged rollout only after metrics are healthy.

## 9) Monitor first 24 hours

In admin dashboard:

1. `Analytics Overview`: success rate, p95 latency, cost.
2. `Provider Health`: failure spikes and queue.
3. `Experiments`: keep risky tests off until baseline is stable.

## 10) If anything breaks

1. Roll back provider settings from `Provider Settings` version history.
2. Disable risky experiment.
3. Roll back Vercel deployment to last stable.
4. Record reason in audit fields (`actor`, `reason`).
