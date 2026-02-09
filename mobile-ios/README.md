# iOS App Scaffold (SwiftUI)

This folder contains a starter architecture for the iOS client.

## Suggested structure

- `App/` app entry and root tab flow
- `Features/Tools` tool cards + render creation flow
- `Features/Create` user board and history
- `Features/Discover` inspiration feed
- `Features/Profile` subscription and settings
- `Networking/` API client and models

## API integration targets

- `GET /v1/config/bootstrap`
- `GET /v1/session/bootstrap/me`
- `POST /v1/ai/render-jobs`
- `GET /v1/ai/render-jobs/{job_id}`
- `POST /v1/analytics/events`

## Implemented scaffold

- Root tabs with `Tools`, `Create`, `Discover`, `My Profile`.
- `Tools` screen includes image URL input, operation/tier selectors, and render polling.
- `Create` screen loads `/v1/projects/board/{user_id}` and renders board cards.
- `Discover` screen loads `/v1/discover/feed` with category filter.
- `Profile` screen loads unified session data via `/v1/session/bootstrap/me` (profile, experiments, catalog).
- `APIClient` supports bootstrap, render flows, board/discover, credits/entitlement, and profile overview.
- `APIClient` performs `POST /v1/auth/login-dev` and sends bearer token for user-scoped endpoints.
- Shared app session across tabs: Profile allows changing the active `user_id`; Tools/Create/Discover/Profile use the same account automatically.

## Build scaffolding

- `project.yml` (XcodeGen) is included to generate an Xcode project from current source folders.
- `Info.plist` is included for app target metadata.
- `App/AppConfig.swift` reads API base URL in this order:
  1) `HOMEAI_API_BASE_URL` environment variable
  2) `APIBaseURL` value from `Info.plist`
  3) fallback `http://localhost:8000`
- ATS local networking is enabled in `Info.plist` for local HTTP testing.

Generate project:
```bash
cd mobile-ios
xcodegen generate
```

Build check (requires full Xcode developer directory):
```bash
sudo xcode-select -switch /Applications/Xcode.app/Contents/Developer
xcodebuild -project HomeAI.xcodeproj -scheme HomeAI -sdk iphonesimulator -configuration Debug build
```

## Run on iOS Simulator

1. Start backend API:
```bash
cd backend-api
uvicorn app.main:app --reload --port 8000
```

2. Generate/open iOS project:
```bash
cd mobile-ios
xcodegen generate
open HomeAI.xcodeproj
```

3. In Xcode:
- Choose `HomeAI` scheme.
- Choose an iPhone simulator (for example `iPhone 15`).
- Press `Cmd+R` to run.

4. Optional: override API URL for testing:
- Edit scheme: `Product > Scheme > Edit Scheme...`
- `Run > Arguments > Environment Variables`
- Add `HOMEAI_API_BASE_URL` (example: `http://localhost:8000`)

## Run unit tests

In Xcode:
- `Product > Test` (`Cmd+U`) with `HomeAITests`.

CLI (build validation):
```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
xcodebuild -project mobile-ios/HomeAI.xcodeproj \
  -scheme HomeAI \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/HomeAIDerived \
  build-for-testing
```
