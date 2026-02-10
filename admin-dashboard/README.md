# Admin Dashboard (Web)

Standalone admin panel for provider settings, styles, plans, variables, provider health, and analytics KPIs.

## Local usage

1. Open `index.html` in a browser, or serve the folder:
   - `cd admin-dashboard`
   - `python3 -m http.server 4173`
2. Set **API Base URL** (for example: `http://localhost:8000`).
3. Add auth values if your backend enforces admin access:
   - `Bearer Token` for `ADMIN_USER_IDS` mode
   - `Admin API Token` for `ADMIN_API_TOKEN` mode
4. Use **Refresh All Data** to load draft settings, plans, variables, provider health, analytics overview, and product audit.

## Build

```bash
cd admin-dashboard
npm run build
```

Build output: `admin-dashboard/dist/`

## Dashboard modules

- Left navigation with:
  - group filters (`Overview`, `Setup`, `AI Routing`, `Monetization`, `Experiments`, `Reliability`, `Audit`)
  - section search
  - quick section jump links
  - `Refresh Visible` to refresh only currently visible sections
- API connection + health check.
- Quick Provider Router controls (default provider, enabled providers, fallback chain, per-operation/part routes, provider model IDs).
- Full JSON editor (draft save/publish/rollback + versions + audit).
- Style catalog CRUD (style ID, name, prompt template, thumbnail URL, tags, room types, sort order, active flag) with visual preview grid.
- Plans CRUD.
- Variables CRUD.
- Experiments (A/B) CRUD + audit.
- Experiment templates for pricing and provider-routing tests (one-click form apply).
- Experiment guardrail run controls (dry-run and live auto-pause enforcement).
- Experiment performance evaluator (variant lift, p-value significance, rollout recommendation).
- Experiment trend explorer (window + bucket controls, per-variant time-series table + chart).
- Performance table includes paid-source cohort split per variant (`web`/`ios`/`android`).
- Experiment auto-rollout evaluator/apply (10% -> 50% -> 100% with guardrail gate).
- Bulk rollout evaluation across active experiments (dry-run/live with per-run limit).
- Automation runner to execute guardrails + bulk rollout in one action.
- Automation history list to review recent unattended runs and outcomes.
- Credits reset scheduler controls (edit schedule, dry-run, run, tick).
- Provider health metrics.
- Analytics KPI dashboard (window filter, provider/operation/platform breakdowns, subscription source mix, funnel conversion, experiment performance, alerts).
- Product audit log.

Analytics alert thresholds are controlled through variables:
- `analytics_alert_min_success_rate_pct`
- `analytics_alert_max_p95_latency_ms`
- `analytics_alert_max_avg_cost_usd`
- `analytics_alert_max_queued_jobs`

## Deploy on Vercel

1. Install and login once:
   - `npm i -g vercel`
   - `vercel login`
2. Deploy from this folder:
   - `cd admin-dashboard`
   - `vercel --prod`

## Backend requirement

If dashboard and backend are on different domains, set backend `ALLOWED_ORIGINS` to include your Vercel domain.

Example:

```
ALLOWED_ORIGINS=https://your-dashboard.vercel.app,http://localhost:4173
```
