# HomeAI Web App (MVP)

Web client for the same backend/account used by iOS and Android.

## Features implemented

- Dev login/session (`/v1/auth/login-dev`, `/v1/auth/me`, `/v1/auth/logout`)
- Unified authenticated bootstrap (`/v1/session/bootstrap/me`) for profile/board/experiments/catalog
- Tools presets + project board (`/v1/projects/board/me`)
- Create/render flow (`/v1/ai/render-jobs`, poll `/v1/ai/render-jobs/{job_id}`)
- Discover feed (`/v1/discover/feed`)
- Profile/credits/entitlement (`/v1/profile/overview/me`)
- Subscription catalog + web checkout session (`/v1/subscriptions/catalog`, `/v1/subscriptions/web/checkout-session`)
- Active experiment assignments (`/v1/experiments/active/{user_id}`)
- Basic analytics events (`/v1/analytics/events`)

## Run locally

1. Start backend API.
2. Serve this folder:
   - `cd web-app`
   - `python3 -m http.server 4180`
3. Open:
   - `http://localhost:4180`
4. Set API Base URL in UI (for example `http://localhost:8000`) and login.

## Build

```bash
cd web-app
npm run build
```

Build output: `web-app/dist/`

## Notes

- This MVP uses image URLs in Create; file upload and storage proxy can be added next.
- Web checkout currently uses backend-generated checkout URL (configure backend `WEB_BILLING_CHECKOUT_BASE_URL`).
- On `?checkout=success`, web app auto-refreshes session bootstrap for a few retries to pick up webhook-applied entitlement.
- For cross-origin calls, backend `ALLOWED_ORIGINS` must include this web app origin.
