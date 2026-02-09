from __future__ import annotations

from datetime import datetime
from app.time_utils import utc_now

from sqlalchemy import desc, func, select

from app.db import session_scope
from app.models import RenderJobModel, UserProjectModel
from app.schemas import (
    ImagePart,
    JobStatus,
    OperationType,
    ProjectBoardItemResponse,
    RenderJobRecord,
    RenderTier,
    UserBoardResponse,
)


def save_render_job(job: RenderJobRecord) -> RenderJobRecord:
    with session_scope() as session:
        model = session.get(RenderJobModel, job.id)
        if not model:
            model = RenderJobModel(id=job.id)
            session.add(model)

        model.project_id = job.project_id
        model.style_id = job.style_id
        model.operation = job.operation.value
        model.tier = job.tier.value
        model.target_parts_json = [part.value for part in job.target_parts]
        model.provider = job.provider
        model.provider_model = job.provider_model
        model.provider_attempts_json = list(job.provider_attempts)
        model.provider_job_id = job.provider_job_id
        model.status = job.status.value
        model.output_url = str(job.output_url) if job.output_url else None
        model.estimated_cost_usd = job.estimated_cost_usd
        model.error_code = job.error_code
        model.created_at = job.created_at
        model.updated_at = job.updated_at

    return job


def get_render_job(job_id: str) -> RenderJobRecord | None:
    with session_scope() as session:
        model = session.get(RenderJobModel, job_id)
        if not model:
            return None
        return _to_schema(model)


def upsert_user_project(user_id: str, project_id: str, cover_image_url: str | None) -> None:
    with session_scope() as session:
        model = session.get(UserProjectModel, project_id)
        if not model:
            model = UserProjectModel(project_id=project_id, user_id=user_id, created_at=utc_now())
            session.add(model)

        model.user_id = user_id
        if cover_image_url:
            model.cover_image_url = cover_image_url
        model.updated_at = utc_now()


def get_user_board(user_id: str, limit: int = 30) -> UserBoardResponse:
    with session_scope() as session:
        membership_stmt = (
            select(UserProjectModel)
            .where(UserProjectModel.user_id == user_id)
            .order_by(desc(UserProjectModel.updated_at))
            .limit(limit)
        )
        memberships = session.execute(membership_stmt).scalars().all()

        projects: list[ProjectBoardItemResponse] = []
        for membership in memberships:
            count_stmt = select(func.count()).select_from(RenderJobModel).where(
                RenderJobModel.project_id == membership.project_id
            )
            generation_count = int(session.execute(count_stmt).scalar_one() or 0)

            latest_stmt = (
                select(RenderJobModel)
                .where(RenderJobModel.project_id == membership.project_id)
                .order_by(desc(RenderJobModel.updated_at))
                .limit(1)
            )
            latest = session.execute(latest_stmt).scalars().first()

            projects.append(
                ProjectBoardItemResponse(
                    project_id=membership.project_id,
                    cover_image_url=membership.cover_image_url,
                    generation_count=generation_count,
                    last_job_id=latest.id if latest else None,
                    last_style_id=latest.style_id if latest else None,
                    last_status=JobStatus(latest.status) if latest else None,
                    last_output_url=latest.output_url if latest and latest.output_url else None,
                    last_updated_at=latest.updated_at if latest else membership.updated_at,
                )
            )

        return UserBoardResponse(user_id=user_id, projects=projects)


def has_completed_preview(project_id: str, style_id: str) -> bool:
    with session_scope() as session:
        stmt = (
            select(RenderJobModel.id)
            .where(
                RenderJobModel.project_id == project_id,
                RenderJobModel.style_id == style_id,
                RenderJobModel.tier == RenderTier.preview.value,
                RenderJobModel.status == JobStatus.completed.value,
            )
            .limit(1)
        )
        found = session.execute(stmt).scalar_one_or_none()
        return found is not None


def update_render_job_status(
    job_id: str,
    *,
    status: JobStatus | None = None,
    output_url: str | None = None,
    error_code: str | None = None,
) -> RenderJobRecord | None:
    with session_scope() as session:
        model = session.get(RenderJobModel, job_id)
        if not model:
            return None

        if status is not None:
            model.status = status.value
        if output_url is not None:
            model.output_url = output_url
        if error_code is not None:
            model.error_code = error_code

        model.updated_at = utc_now()
        session.flush()
        session.refresh(model)
        return _to_schema(model)


def _to_schema(model: RenderJobModel) -> RenderJobRecord:
    return RenderJobRecord(
        id=model.id,
        project_id=model.project_id,
        style_id=model.style_id,
        operation=OperationType(model.operation),
        tier=RenderTier(model.tier),
        target_parts=[ImagePart(item) for item in (model.target_parts_json or [])],
        provider=model.provider,
        provider_model=model.provider_model,
        provider_attempts=list(model.provider_attempts_json or []),
        provider_job_id=model.provider_job_id,
        status=JobStatus(model.status),
        output_url=model.output_url,
        estimated_cost_usd=model.estimated_cost_usd,
        created_at=model.created_at,
        updated_at=model.updated_at,
        error_code=model.error_code,
    )
