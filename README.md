# HomeAI Universal Platform

Unified product stack for AI home/interior generation:
- `backend-api/` FastAPI orchestration, subscriptions, experiments, analytics
- `web-app/` user-facing web client
- `admin-dashboard/` operations + pricing/provider analytics console
- `mobile-ios/` SwiftUI app
- `android-app/` Kotlin Compose app

## Quick start

### 1) Backend

```bash
cd backend-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2) Web app

```bash
cd web-app
python3 -m http.server 4180
```

### 3) Admin dashboard

```bash
cd admin-dashboard
python3 -m http.server 4173
```

## Release commands

- Full preflight:

```bash
./scripts/release_preflight.sh
```

- Backend image (local):

```bash
cd backend-api
docker build -t homeai-backend:local .
```

## Release documentation

- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/launch-readiness-checklist.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/admin-activation-playbook.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/release-and-operations-runbook.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/github-production-setup.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/ab-testing-scenarios.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/universal-platform-implementation-plan.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/web-first-step-by-step-plan.md`
- `/Users/narcadeteknolojiltd.sti./Documents/New project/docs/final-step-by-step-actions.md`
