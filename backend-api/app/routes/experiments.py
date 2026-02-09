from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import assert_same_user, get_authenticated_user, require_admin_access
from app.experiment_store import (
    assign_active_experiments_for_user,
    assign_experiment,
    evaluate_and_apply_all_experiment_rollouts,
    delete_experiment,
    evaluate_and_apply_experiment_rollout,
    evaluate_experiment_guardrails,
    get_experiment_performance,
    get_experiment_trends,
    list_experiment_automation_history,
    list_experiment_templates,
    list_experiment_audit,
    list_experiments,
    run_experiment_automation,
    upsert_experiment,
)
from app.schemas import (
    ActiveExperimentAssignmentsResponse,
    AdminActionRequest,
    AuditLogEntry,
    ExperimentAssignRequest,
    ExperimentAssignResponse,
    ExperimentAutomationRunResponse,
    ExperimentBulkRolloutEvaluationResponse,
    ExperimentConfig,
    ExperimentGuardrailRunResponse,
    ExperimentPerformanceResponse,
    ExperimentRolloutEvaluationResponse,
    ExperimentTrendResponse,
    ExperimentTemplate,
    ExperimentUpsertRequest,
)

router = APIRouter(prefix="/v1/experiments", tags=["experiments"])
admin_router = APIRouter(
    prefix="/v1/admin/experiments",
    tags=["admin", "experiments"],
    dependencies=[Depends(require_admin_access)],
)


@router.post("/assign", response_model=ExperimentAssignResponse)
async def assign_experiment_variant(
    payload: ExperimentAssignRequest,
    auth_user_id: str = Depends(get_authenticated_user),
) -> ExperimentAssignResponse:
    assert_same_user(auth_user_id, payload.user_id)
    try:
        return assign_experiment(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/active/{user_id}", response_model=ActiveExperimentAssignmentsResponse)
async def active_experiment_assignments(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    auth_user_id: str = Depends(get_authenticated_user),
) -> ActiveExperimentAssignmentsResponse:
    assert_same_user(auth_user_id, user_id)
    assignments = assign_active_experiments_for_user(user_id=user_id, limit=limit)
    return ActiveExperimentAssignmentsResponse(user_id=user_id, assignments=assignments)


@admin_router.get("", response_model=list[ExperimentConfig])
async def admin_list_experiments(limit: int = Query(default=200, ge=1, le=1000)) -> list[ExperimentConfig]:
    return list_experiments(limit=limit)


@admin_router.get("/templates", response_model=list[ExperimentTemplate])
async def admin_list_experiment_templates() -> list[ExperimentTemplate]:
    return list_experiment_templates()


@admin_router.put("/{experiment_id}", response_model=ExperimentConfig)
async def admin_upsert_experiment(
    experiment_id: str,
    payload: ExperimentUpsertRequest,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> ExperimentConfig:
    try:
        return upsert_experiment(
            experiment_id=experiment_id,
            payload=payload,
            action=AdminActionRequest(actor=actor, reason=reason),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.delete("/{experiment_id}")
async def admin_delete_experiment(
    experiment_id: str,
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> dict[str, bool]:
    deleted = delete_experiment(
        experiment_id=experiment_id,
        action=AdminActionRequest(actor=actor, reason=reason),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="experiment_not_found")
    return {"deleted": True}


@admin_router.get("/audit", response_model=list[AuditLogEntry])
async def admin_experiment_audit(limit: int = Query(default=100, ge=1, le=1000)) -> list[AuditLogEntry]:
    return list_experiment_audit(limit=limit)


@admin_router.post("/guardrails/evaluate", response_model=ExperimentGuardrailRunResponse)
async def admin_evaluate_experiment_guardrails(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    dry_run: bool = Query(default=True),
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> ExperimentGuardrailRunResponse:
    return evaluate_experiment_guardrails(
        hours=hours,
        dry_run=dry_run,
        action=AdminActionRequest(actor=actor, reason=reason),
    )


@admin_router.get("/{experiment_id}/performance", response_model=ExperimentPerformanceResponse)
async def admin_experiment_performance(
    experiment_id: str,
    hours: int = Query(default=24, ge=1, le=24 * 30),
) -> ExperimentPerformanceResponse:
    try:
        return get_experiment_performance(experiment_id=experiment_id, hours=hours)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.get("/{experiment_id}/trends", response_model=ExperimentTrendResponse)
async def admin_experiment_trends(
    experiment_id: str,
    hours: int = Query(default=24 * 7, ge=1, le=24 * 60),
    bucket_hours: int = Query(default=24, ge=1, le=24 * 14),
) -> ExperimentTrendResponse:
    try:
        return get_experiment_trends(
            experiment_id=experiment_id,
            hours=hours,
            bucket_hours=bucket_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.post("/{experiment_id}/rollout/evaluate", response_model=ExperimentRolloutEvaluationResponse)
async def admin_evaluate_experiment_rollout(
    experiment_id: str,
    hours: int = Query(default=24 * 7, ge=1, le=24 * 60),
    dry_run: bool = Query(default=True),
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> ExperimentRolloutEvaluationResponse:
    try:
        return evaluate_and_apply_experiment_rollout(
            experiment_id=experiment_id,
            hours=hours,
            dry_run=dry_run,
            action=AdminActionRequest(actor=actor, reason=reason),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.post("/rollout/evaluate-all", response_model=ExperimentBulkRolloutEvaluationResponse)
async def admin_evaluate_all_experiment_rollouts(
    hours: int = Query(default=24 * 7, ge=1, le=24 * 60),
    dry_run: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> ExperimentBulkRolloutEvaluationResponse:
    return evaluate_and_apply_all_experiment_rollouts(
        hours=hours,
        dry_run=dry_run,
        limit=limit,
        action=AdminActionRequest(actor=actor, reason=reason),
    )


@admin_router.post("/automation/run", response_model=ExperimentAutomationRunResponse)
async def admin_run_experiment_automation(
    hours: int = Query(default=24 * 7, ge=1, le=24 * 60),
    dry_run: bool = Query(default=True),
    rollout_limit: int = Query(default=200, ge=1, le=1000),
    actor: str = Query(default="dashboard"),
    reason: str | None = Query(default=None),
) -> ExperimentAutomationRunResponse:
    return run_experiment_automation(
        hours=hours,
        dry_run=dry_run,
        rollout_limit=rollout_limit,
        action=AdminActionRequest(actor=actor, reason=reason),
    )


@admin_router.get("/automation/history", response_model=list[AuditLogEntry])
async def admin_experiment_automation_history(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[AuditLogEntry]:
    return list_experiment_automation_history(limit=limit)
