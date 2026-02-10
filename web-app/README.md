# HomeAI Web App

Web client for the same backend/account used by iOS and Android.

## Features implemented

- Mobile-first end-user flow with bottom navigation.
- 4-step create wizard:
  - Step 1: image input + preview.
  - Step 2: room type selection.
  - Step 3: style selection with thumbnails.
  - Step 3: custom style creation (name + prompt + thumbnail URL) persisted in browser storage.
  - Step 4: review + render submission.
- Render flow on shared backend (`/v1/ai/render-jobs`, poll `/v1/ai/render-jobs/{job_id}`).
- Unified authenticated bootstrap (`/v1/session/bootstrap/me`) for profile/board/catalog.
- Discover feed (`/v1/discover/feed`).
- Subscription catalog + web checkout session (`/v1/subscriptions/catalog`, `/v1/subscriptions/web/checkout-session`).

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

- Current create flow uses image URL input. If you want direct file upload, add backend upload endpoint and swap Step 1 input.
- Web checkout uses backend-generated checkout URL (`WEB_BILLING_CHECKOUT_BASE_URL`).
- For cross-origin calls, backend `ALLOWED_ORIGINS` must include this web app origin.
- On public domains, do not use `localhost` as API URL. Configure `API Base URL` from `Settings` to your production backend domain.
