from __future__ import annotations

from uuid import uuid4

from app.schemas import JobStatus, ProviderDispatchRequest, ProviderDispatchResult, ProviderStatusResult


class MockProvider:
    """Test provider useful for staging and CI."""

    name = "mock"

    async def submit(self, request: ProviderDispatchRequest) -> ProviderDispatchResult:
        request_id = str(uuid4())
        return ProviderDispatchResult(
            provider_job_id=request_id,
            status=JobStatus.completed,
            output_url=f"https://cdn.example.com/mock/{request_id}.jpg",
            estimated_cost_usd=0.0,
        )

    async def get_status(self, provider_job_id: str, model_id: str) -> ProviderStatusResult:
        return ProviderStatusResult(
            status=JobStatus.completed,
            output_url=f"https://cdn.example.com/mock/{provider_job_id}.jpg",
        )

    async def cancel(self, provider_job_id: str, model_id: str) -> bool:
        return True
