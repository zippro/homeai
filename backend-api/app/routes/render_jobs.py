from __future__ import annotations

import hashlib
import time
from datetime import datetime
from app.time_utils import utc_now
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.analytics_store import ingest_event
from app.auth import assert_same_user, get_optional_authenticated_user
from app.credit_store import consume_credits, grant_credits
from app.job_store import (
    get_render_job,
    has_completed_preview,
    save_render_job,
    update_render_job_status,
    upsert_user_project,
)
from app.product_store import get_plan, get_variable_map
from app.providers.registry import get_provider_registry
from app.render_policy import resolve_credit_cost, should_block_final_without_preview
from app.router import resolve_model, resolve_provider_candidates
from app.schemas import (
    AnalyticsEventRequest,
    CancelJobResponse,
    CreditConsumeRequest,
    CreditGrantRequest,
    JobStatus,
    ProviderDispatchRequest,
    RenderJobCreateRequest,
    RenderJobRecord,
    RenderJobStatusResponse,
    RenderTier,
)
from app.settings_store import get_provider_settings
from app.subscription_store import get_entitlement

router = APIRouter(prefix="/v1/ai", tags=["ai"])

_TERMINAL_STATUSES = {JobStatus.completed, JobStatus.failed, JobStatus.canceled}


def _build_prompt(payload: RenderJobCreateRequest) -> str:
    parts_csv = ",".join([part.value for part in payload.target_parts])
    base = (
        f"Apply {payload.style_id} style for operation={payload.operation.value}; "
        f"target_parts={parts_csv}; preserve room geometry and lighting consistency."
    )
    if payload.prompt_overrides:
        return f"{base} Overrides: {payload.prompt_overrides}"
    return base


@router.post("/render-jobs", response_model=RenderJobRecord)
async def create_render_job(
    payload: RenderJobCreateRequest,
    auth_user_id: str | None = Depends(get_optional_authenticated_user),
) -> RenderJobRecord:
    settings = get_provider_settings()
    registry = get_provider_registry()
    variables = get_variable_map()
    preview_before_final_required = bool(variables.get("preview_before_final_required", True))
    daily_credit_limit_enabled = bool(variables.get("daily_credit_limit_enabled", True))

    if payload.user_id:
        if not auth_user_id:
            raise HTTPException(status_code=401, detail="authentication_required_for_user_jobs")
        assert_same_user(auth_user_id, payload.user_id)

    if should_block_final_without_preview(
        preview_before_final_required=preview_before_final_required,
        tier=payload.tier,
        has_completed_preview=has_completed_preview(payload.project_id, payload.style_id),
    ):
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_blocked_preview_required",
                user_id=payload.user_id,
                platform=payload.platform,
                operation=payload.operation,
                status=JobStatus.failed,
            )
        )
        raise HTTPException(status_code=409, detail="preview_required_before_final")

    credit_cost = 0
    idempotency_key = None
    if payload.user_id:
        entitlement = get_entitlement(payload.user_id)
        effective_plan_id = entitlement.plan_id if entitlement.status.value == "active" else "free"
        plan = get_plan(effective_plan_id) or get_plan("free")
        preview_cost = plan.preview_cost_credits if plan else 1
        final_cost = plan.final_cost_credits if plan else 2
        credit_cost = resolve_credit_cost(preview_cost, final_cost, payload.tier)
        key_src = f"{payload.user_id}|{payload.project_id}|{payload.style_id}|{payload.tier.value}|{payload.image_url}"
        idempotency_key = f"rdr_{hashlib.sha256(key_src.encode('utf-8')).hexdigest()[:48]}"
        if daily_credit_limit_enabled and credit_cost > 0:
            try:
                consume_credits(
                    CreditConsumeRequest(
                        user_id=payload.user_id,
                        amount=credit_cost,
                        reason=f"render_{payload.tier.value}",
                        idempotency_key=idempotency_key,
                        metadata={
                            "plan_id": effective_plan_id,
                            "tier": payload.tier.value,
                        },
                    )
                )
            except ValueError as exc:
                ingest_event(
                    AnalyticsEventRequest(
                        event_name="render_blocked_insufficient_credits",
                        user_id=payload.user_id,
                        platform=payload.platform,
                        operation=payload.operation,
                        status=JobStatus.failed,
                    )
                )
                raise HTTPException(status_code=402, detail=str(exc)) from exc

    try:
        candidate_providers = resolve_provider_candidates(
            settings=settings,
            operation=payload.operation,
            tier=payload.tier,
            target_parts=payload.target_parts,
            available_providers=set(registry.keys()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attempted_providers: list[str] = []
    attempt_errors: dict[str, str] = {}
    provider_result = None
    selected_provider = None
    selected_model = None
    dispatch_latency_ms = 0

    for provider_name in candidate_providers:
        attempted_providers.append(provider_name)
        try:
            model_id = resolve_model(settings, provider_name, payload.tier)
            provider = registry[provider_name]
            dispatch_request = ProviderDispatchRequest(
                prompt=_build_prompt(payload),
                image_url=payload.image_url,
                mask_url=payload.mask_url,
                model_id=model_id,
                operation=payload.operation,
                tier=payload.tier,
                target_parts=payload.target_parts,
            )

            started_at = time.perf_counter()
            provider_result = await provider.submit(dispatch_request)
            dispatch_latency_ms = int((time.perf_counter() - started_at) * 1000)

            selected_provider = provider_name
            selected_model = model_id
            break
        except Exception as exc:  # noqa: BLE001
            attempt_errors[provider_name] = str(exc)
            ingest_event(
                AnalyticsEventRequest(
                    event_name="render_provider_attempt_failed",
                    user_id=payload.user_id,
                    platform=payload.platform,
                    provider=provider_name,
                    operation=payload.operation,
                    status=JobStatus.failed,
                )
            )

    if not provider_result or not selected_provider or not selected_model:
        if payload.user_id and daily_credit_limit_enabled and credit_cost > 0 and idempotency_key:
            try:
                grant_credits(
                    CreditGrantRequest(
                        user_id=payload.user_id,
                        amount=credit_cost,
                        reason="render_refund_dispatch_failed",
                        idempotency_key=f"refund_{idempotency_key}",
                    )
                )
            except ValueError:
                # Keep returning dispatch failure as primary error.
                pass
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_dispatch_failed",
                user_id=payload.user_id,
                platform=payload.platform,
                provider=attempted_providers[0] if attempted_providers else None,
                operation=payload.operation,
                status=JobStatus.failed,
            )
        )
        raise HTTPException(
            status_code=502,
            detail={
                "code": "provider_dispatch_failed",
                "attempts": attempt_errors,
                "candidate_providers": candidate_providers,
            },
        )

    job = RenderJobRecord(
        project_id=payload.project_id,
        style_id=payload.style_id,
        operation=payload.operation,
        tier=payload.tier,
        target_parts=payload.target_parts,
        provider=selected_provider,
        provider_model=selected_model,
        provider_attempts=attempted_providers,
        provider_job_id=provider_result.provider_job_id,
        status=provider_result.status,
        output_url=provider_result.output_url,
        estimated_cost_usd=provider_result.estimated_cost_usd,
        updated_at=utc_now(),
    )

    save_render_job(job)
    if payload.user_id:
        upsert_user_project(payload.user_id, payload.project_id, str(payload.image_url))

    ingest_event(
        AnalyticsEventRequest(
            event_name="render_dispatched",
            user_id=payload.user_id,
            platform=payload.platform,
            provider=selected_provider,
            operation=payload.operation,
            status=provider_result.status,
            latency_ms=dispatch_latency_ms,
            cost_usd=provider_result.estimated_cost_usd,
        )
    )

    return job


@router.get("/render-jobs/{job_id}", response_model=RenderJobStatusResponse)
async def get_render_job_status(job_id: str) -> RenderJobStatusResponse:
    registry = get_provider_registry()
    job = get_render_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")

    if job.status not in _TERMINAL_STATUSES:
        provider = registry.get(job.provider)
        if provider:
            old_status = job.status
            try:
                status_result = await provider.get_status(job.provider_job_id, job.provider_model)
                job = update_render_job_status(
                    job_id=job.id,
                    status=status_result.status,
                    output_url=str(status_result.output_url) if status_result.output_url else None,
                    error_code=status_result.error_code,
                ) or job

                if old_status != status_result.status:
                    ingest_event(
                        AnalyticsEventRequest(
                            event_name="render_status_updated",
                            provider=job.provider,
                            operation=job.operation,
                            status=job.status,
                            cost_usd=job.estimated_cost_usd,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                job = update_render_job_status(
                    job_id=job.id,
                    error_code=f"status_poll_error:{exc}",
                ) or job

    return RenderJobStatusResponse(
        id=job.id,
        status=job.status,
        provider=job.provider,
        provider_model=job.provider_model,
        output_url=job.output_url,
        estimated_cost_usd=job.estimated_cost_usd,
        updated_at=job.updated_at,
        error_code=job.error_code,
    )


@router.post("/render-jobs/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_render_job(job_id: str) -> CancelJobResponse:
    registry = get_provider_registry()
    job = get_render_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")

    provider = registry.get(job.provider)
    canceled = False
    if provider and job.status not in _TERMINAL_STATUSES:
        try:
            canceled = await provider.cancel(job.provider_job_id, job.provider_model)
        except Exception:  # noqa: BLE001
            canceled = False

    if canceled:
        job = update_render_job_status(job.id, status=JobStatus.canceled) or job
        ingest_event(
            AnalyticsEventRequest(
                event_name="render_canceled",
                provider=job.provider,
                operation=job.operation,
                status=job.status,
            )
        )

    return CancelJobResponse(id=job_id, canceled=canceled, status=job.status)


@router.get("/providers", response_model=dict[str, Any])
async def list_registered_providers() -> dict[str, Any]:
    registry = get_provider_registry()
    settings = get_provider_settings()
    return {
        "registered": list(registry.keys()),
        "enabled": settings.enabled_providers,
        "default": settings.default_provider,
        "fallback_chain": settings.fallback_chain,
    }
