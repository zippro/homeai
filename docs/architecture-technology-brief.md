# HomeAI Architecture & Technology Brief

## 1) Executive Summary

HomeAI is a multi-surface product with:
- Mobile clients for **iOS** and **Android**.
- A **Web app** for end-users (same account/session model).
- A **FastAPI backend** that handles auth, AI orchestration, credits, subscriptions, analytics, and configuration.
- A **web Admin Dashboard** used to control providers, plans, variables, and rollout decisions without redeploying backend code.

Core design principle: keep provider, pricing, and behavior controls dynamic via admin-managed configuration and audited versioning.

## 2) High-Level Architecture

```mermaid
flowchart LR
    IOS["iOS App (SwiftUI)"] --> API["Backend API (FastAPI)"]
    AND["Android App (Kotlin + Compose)"] --> API
    WEB["Web App (User)"] --> API
    ADM["Admin Dashboard (HTML/CSS/JS)"] --> API

    API --> AUTH["Auth + Session Layer"]
    API --> CFG["Config + Product Controls"]
    API --> ORCH["AI Render Orchestrator"]
    API --> BILL["Credits + Subscription Logic"]
    API --> ANA["Analytics Ingest + Health"]

    ORCH --> ROUTE["Provider Router"]
    ROUTE --> FAL["fal.ai Provider Adapter"]
    ROUTE --> OAI["OpenAI Provider Adapter"]
    ROUTE --> MOCK["Mock Provider Adapter"]

    OAI --> S3["S3-Compatible Storage (b64 upload path)"]

    AUTH --> DB["SQLAlchemy + SQLite/Postgres-compatible DB"]
    CFG --> DB
    ORCH --> DB
    BILL --> DB
    ANA --> DB

    classDef app fill:#fdf2f8,stroke:#be185d,color:#9d174d;
    classDef svc fill:#eff6ff,stroke:#2563eb,color:#1d4ed8;
    classDef ext fill:#ecfdf5,stroke:#059669,color:#065f46;
    classDef data fill:#fff7ed,stroke:#ea580c,color:#9a3412;

    class IOS,AND,WEB,ADM app;
    class API,AUTH,CFG,ORCH,BILL,ANA,ROUTE svc;
    class FAL,OAI,MOCK,S3 ext;
    class DB data;
```

## 3) Technology Stack

| Layer | Technologies in Use |
|---|---|
| Backend API | Python, FastAPI, Pydantic, SQLAlchemy, Uvicorn, httpx, boto3 |
| AI Provider Integrations | fal.ai Queue API adapter, OpenAI Images API adapter, Mock adapter |
| Data & Persistence | SQLAlchemy ORM models; default SQLite (`app.db`), Postgres-compatible design |
| Admin Panel | Vanilla HTML, CSS, JavaScript (single-page control room), Vercel-ready deploy config |
| Web App | Vanilla HTML, CSS, JavaScript MVP (same API contracts as mobile) |
| iOS Client | Swift, SwiftUI, async/await networking (`URLSession`), XcodeGen project setup |
| Android Client | Kotlin, Jetpack Compose, Material3, Coroutines, Gradle Kotlin DSL |
| CI / Quality | GitHub Actions backend quality workflow + `make quality` (tests + compile check) |

## 4) Admin Panel Architecture

### Admin modules shipped
- API connection + health test
- Provider settings draft/publish/rollback
- Provider settings version history + audit trail
- Plans CRUD
- Variables CRUD
- Provider health table (request count, success rate, latency)
- Activity log console

### Admin-to-backend control path

```mermaid
flowchart TD
    UI["Admin Control Room UI"] --> ENDP["/v1/admin/* endpoints"]
    ENDP --> SVC["Store/Service layer"]
    SVC --> DB["Config + Audit + Product tables"]
    SVC --> RESP["Updated settings / versions / health metrics"]
    RESP --> UI
```

## 5) Render Request Flow (Mobile -> Provider -> Result)

```mermaid
sequenceDiagram
    participant App as Mobile App
    participant API as FastAPI
    participant Router as Provider Router
    participant Prov as Provider (fal/openai/mock)
    participant DB as Database

    App->>API: POST /v1/ai/render-jobs
    API->>API: Validate auth, plan, credits, policy gates
    API->>Router: Resolve provider candidates + model
    Router->>Prov: Submit render request
    Prov-->>API: Provider job id/status
    API->>DB: Save render job + attempts + project
    API-->>App: Job record

    App->>API: GET /v1/ai/render-jobs/{job_id}
    API->>Prov: Poll status (if non-terminal)
    Prov-->>API: Status/output
    API->>DB: Update job state/output/error
    API-->>App: Current job status
```

## 6) Key Backend Domains

- `auth`: dev login, token validation, session lifecycle
- `config`: mobile bootstrap data (active plans, variables, provider defaults)
- `ai/render-jobs`: orchestration, provider routing, status polling, cancel
- `credits`: consume/grant, balance checks, daily reset schedule support
- `subscriptions`: entitlement APIs + StoreKit/Google Play webhook stubs
- `experiments`: A/B experiment definitions, sticky assignments, and experiment audit
- `projects/discover/profile`: user board, inspiration feed, profile overview
- `admin`: provider/product management + analytics/provider-health visibility

## 7) Platform Delivery Shape

```mermaid
pie title Product Surfaces (Architecture Focus)
    "Backend API Core" : 35
    "Admin Dashboard" : 20
    "iOS App" : 22
    "Android App" : 23
```

Note: chart proportions are a communication view of architecture focus (not LOC metrics).

## 8) Current Status Snapshot

- Backend orchestration and admin-control endpoints are implemented and wired.
- Admin dashboard is functional and directly connected to live backend endpoints.
- iOS and Android clients include tab-based scaffold + API-integrated core screens (`Tools`, `Create`, `Discover`, `My Profile`).
- Web app MVP now uses the same backend contracts for auth, render jobs, discover, profile, and subscriptions.
- iOS/Android/Web now share the same logical user-session pattern (`homeai_demo_user` by default, editable from profile/web UI).
- CI currently enforces backend quality checks via GitHub Actions.
