from __future__ import annotations

from fastapi import FastAPI

from app.bootstrap import init_database
from app.routes.admin_product import router as admin_product_router
from app.routes.admin_settings import router as admin_router
from app.routes.analytics import router as analytics_router
from app.routes.config import router as config_router
from app.routes.credit_reset import router as credit_reset_router
from app.routes.credits import router as credits_router
from app.routes.discover import router as discover_router
from app.routes.provider_health import router as provider_health_router
from app.routes.projects import router as projects_router
from app.routes.render_jobs import router as render_router
from app.routes.subscriptions import admin_router as admin_subscriptions_router
from app.routes.subscriptions import router as subscriptions_router
from app.routes.webhooks import router as webhooks_router

app = FastAPI(
    title="AI Interior Orchestrator API",
    version="0.5.0",
    description=(
        "Provider-flexible image generation/editing backend for iOS and Android apps "
        "with dashboard-driven provider/plan/variable controls."
    ),
)


@app.on_event("startup")
async def on_startup() -> None:
    init_database()


app.include_router(admin_router)
app.include_router(admin_product_router)
app.include_router(render_router)
app.include_router(projects_router)
app.include_router(discover_router)
app.include_router(analytics_router)
app.include_router(config_router)
app.include_router(credits_router)
app.include_router(credit_reset_router)
app.include_router(subscriptions_router)
app.include_router(admin_subscriptions_router)
app.include_router(provider_health_router)
app.include_router(webhooks_router)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
