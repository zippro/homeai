from __future__ import annotations

from typing import Protocol

from app.schemas import ProviderDispatchRequest, ProviderDispatchResult, ProviderStatusResult


class ImageProvider(Protocol):
    name: str

    async def submit(self, request: ProviderDispatchRequest) -> ProviderDispatchResult:
        """Submit image generation/edit request to provider."""

    async def get_status(self, provider_job_id: str, model_id: str) -> ProviderStatusResult:
        """Get provider-level request status and output metadata."""

    async def cancel(self, provider_job_id: str, model_id: str) -> bool:
        """Attempt to cancel provider-level request."""
