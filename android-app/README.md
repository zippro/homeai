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
- `GET /v1/session/bootstrap/me`
- `POST /v1/ai/render-jobs`
- `GET /v1/ai/render-jobs/{job_id}`
- `GET /v1/projects/board/{user_id}`
- `GET /v1/discover/feed`
- `GET /v1/credits/balance/{user_id}`
- `GET /v1/subscriptions/entitlements/{user_id}`
- `GET /v1/profile/overview/{user_id}`

## Implemented scaffold

- Root tabs with `Tools`, `Create`, `Discover`, `My Profile`.
- `Tools` screen includes image URL, style input, and render submit.
- `Create` screen pulls user board from backend.
- `Discover` screen pulls feed from backend.
- `Profile` screen pulls unified session payload (`/v1/session/bootstrap/me`) for profile, catalog, and experiments.
- `ApiClient` supports render, board, discover, credits, entitlement, and profile overview.
- `ApiClient` performs `POST /v1/auth/login-dev` and sends bearer token for user-scoped endpoints.
- Shared app session across tabs: Profile allows changing active `user_id`; Tools/Create/Discover/Profile all use the same account.
- Manifest enables `android:usesCleartextTraffic="true"` for local HTTP API testing (`http://10.0.2.2:8000`).

## Build scaffolding

- Gradle Kotlin DSL files are included (`settings.gradle.kts`, root/app `build.gradle.kts`).
- Manifest/resources are included for a runnable Compose app shell.

Example build:
```bash
cd android-app
./gradlew assembleDebug
```

If wrapper is missing in your environment, generate it once with `gradle wrapper`.
If Android SDK is not auto-detected, create `local.properties`:
```properties
sdk.dir=/Users/<your-user>/Library/Android/sdk
```
