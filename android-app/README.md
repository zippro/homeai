# Android App Scaffold (Kotlin + Compose)

Starter architecture for Android client aligned to iOS UX and backend contract.

## Suggested modules

- `app`: UI shell and navigation
- `core/network`: API client and DTOs
- `feature/tools`
- `feature/create`
- `feature/discover`
- `feature/profile`

## API integration targets

- `GET /v1/config/bootstrap`
- `POST /v1/ai/render-jobs`
- `GET /v1/ai/render-jobs/{job_id}`
- `GET /v1/projects/board/{user_id}`
- `GET /v1/discover/feed`
- `GET /v1/credits/balance/{user_id}`
- `GET /v1/subscriptions/entitlements/{user_id}`

## Implemented scaffold

- Root tabs with `Tools`, `Create`, `Discover`, `My Profile`.
- `Tools` screen includes image URL, style input, and render submit.
- `Create` screen pulls user board from backend.
- `Discover` screen pulls feed from backend.
- `Profile` screen pulls credits + entitlement.
- `ApiClient` supports render, board, discover, credits, entitlement.
