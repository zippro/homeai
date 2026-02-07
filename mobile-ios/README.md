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
- `POST /v1/ai/render-jobs`
- `GET /v1/ai/render-jobs/{job_id}`
- `POST /v1/analytics/events`

## Implemented scaffold

- Root tabs with `Tools`, `Create`, `Discover`, `My Profile`.
- `Tools` screen includes image URL input, operation/tier selectors, and render polling.
- `Create` screen loads `/v1/projects/board/{user_id}` and renders board cards.
- `Discover` screen loads `/v1/discover/feed` with category filter.
- `Profile` screen loads credits and subscription entitlement.
- `APIClient` supports bootstrap, render flows, board/discover, credits, and entitlement.
