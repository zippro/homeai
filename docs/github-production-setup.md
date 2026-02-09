# GitHub Production Setup (homeai)

Repository: `zippro/homeai`

This guide configures GitHub so releases are safe and reproducible.

## 1) Required repository secrets

Set these in **Settings -> Secrets and variables -> Actions -> Repository secrets**.

### Vercel deploy

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_WEB_PROJECT_ID`
- `VERCEL_ADMIN_PROJECT_ID`

### Backend/runtime credentials

- `FAL_API_KEY`
- `OPENAI_API_KEY` (optional if not using OpenAI provider)
- `STOREKIT_WEBHOOK_SECRET`
- `GOOGLE_PLAY_WEBHOOK_SECRET`
- `WEB_BILLING_WEBHOOK_SECRET`
- `ADMIN_API_TOKEN`

## 2) Recommended branch protection for `main`

Enable in **Settings -> Branches**:

- Require pull request before merging.
- Require at least 1 approval.
- Dismiss stale reviews on new commits.
- Require conversation resolution.
- Require linear history.
- Disable force pushes.
- Disable branch deletion.

Required status checks:

- `Backend Quality / quality`
- `Web Admin Quality / syntax-check`
- `Android Quality / compile`
- `iOS Quality / build`

## 3) Deployment workflows

- `Deploy Web and Admin` (manual)
  - choose `web`, `admin`, or `both`
  - choose production or preview deploy
- `Backend Image`
  - auto-builds GHCR image from `main`
- `Release Readiness`
  - full cross-platform quality gate before tag/release

## 4) First production cut (recommended order)

1. Merge release candidate to `main`.
2. Run `Release Readiness` workflow manually.
3. Run `Deploy Web and Admin` with `both` + production.
4. Deploy backend image to production infrastructure.
5. Verify health checks and analytics dashboard.
6. Create tag `vX.Y.Z`.

## 5) Optional automation via CLI

If you want branch-protection automation, use:

```bash
./scripts/github/set_branch_protection.sh zippro/homeai main
```
