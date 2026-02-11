# Backend Hosting Plan (No Existing Server)

If you do not have a backend server, use a managed platform first.

Recommended order:
1. Railway (fastest setup with Docker + Postgres).
2. Render (stable managed web service + managed Postgres).
3. VPS (Hetzner/DigitalOcean) only if you want full infra control.

## Why not Vercel for this backend

This backend is a long-running FastAPI service with:
- DB-backed state,
- webhook endpoints,
- background-like operational flows,
- provider routing and admin APIs.

Vercel Python is function/serverless-oriented, not the best fit for this always-on backend model.

Reference:
- [Vercel Python Runtime docs](https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python)

## Option A (Recommended): Railway

Railway supports Dockerfile deployments and a PostgreSQL service in the same project.

References:
- [Railway Dockerfiles](https://docs.railway.com/deploy/dockerfiles)
- [Railway Services](https://docs.railway.com/guides/services)
- [Railway PostgreSQL](https://docs.railway.com/databases/postgresql/)

### Step-by-step

1. Create Railway account and new project.
2. Add PostgreSQL service (`+ New` -> PostgreSQL).
3. Add backend service from GitHub repo `zippro/homeai`.
4. Set backend service source path to `backend-api` so Railway uses `backend-api/Dockerfile`.
5. Set environment variables in backend service:
   - `APP_ENV=production`
   - `ALLOW_OPEN_ADMIN_MODE=false`
   - `DATABASE_URL` (from Railway Postgres service)
   - `ALLOWED_ORIGINS=https://<your-web-domain>,https://<your-admin-domain>`
   - `ADMIN_API_TOKEN=<strong-secret>`
   - `FAL_API_KEY=<your-key>`
   - `OPENAI_API_KEY=<optional>`
   - `STOREKIT_WEBHOOK_SECRET=<secret>`
   - `GOOGLE_PLAY_WEBHOOK_SECRET=<secret>`
   - `WEB_BILLING_WEBHOOK_SECRET=<secret>`
6. Deploy service and wait until healthy.
7. Copy Railway public backend URL.
8. Run verification:
   - `GET /healthz`
   - `GET /v1/config/provider-route-preview`
9. Put backend URL into:
   - web app settings panel (`API Base URL`)
   - admin dashboard settings panel (`API Base URL`)
10. Add custom domain for backend (optional but recommended), then update `ALLOWED_ORIGINS`.

## Option B: Render

Render supports Docker web services and managed Postgres.

References:
- [Render Web Services](https://render.com/docs/web-services)
- [Docker on Render](https://render.com/docs/docker)
- [Render Postgres](https://render.com/docs/postgresql)

### Step-by-step

1. Create Render account.
2. Create Render Postgres database.
3. Create Web Service from GitHub repo `zippro/homeai`.
4. Configure:
   - Runtime: Docker
   - Root directory: `backend-api`
   - Start binds to `0.0.0.0` and uses platform port.
5. Set the same env vars listed in Railway section.
6. Deploy service and verify health + route preview endpoints.
7. Point web/admin frontends to Render backend URL.

## Option C: VPS (when you want infra ownership)

Use provided templates:
- `deploy/docker-compose.production-template.yml`
- `deploy/backend-api.env.production.example`
- `deploy/Caddyfile.template`

Use this only after managed option is stable.

## Cutover checklist (any platform)

1. `GET /healthz` returns `{"status":"ok"}`.
2. `GET /v1/config/provider-route-preview?...` returns provider/model JSON.
3. Admin dashboard can connect and load analytics + styles + plans.
4. Web app can login and generate one render.
5. Webhook endpoints configured with production secrets.
