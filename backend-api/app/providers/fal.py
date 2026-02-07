from __future__ import annotations

import os
from typing import Any

import httpx

from app.schemas import (
    JobStatus,
    ProviderDispatchRequest,
    ProviderDispatchResult,
    ProviderStatusResult,
    RenderTier,
)

_FAL_STATUS_MAP = {
    "IN_QUEUE": JobStatus.queued,
    "IN_PROGRESS": JobStatus.in_progress,
    "COMPLETED": JobStatus.completed,
    "FAILED": JobStatus.failed,
    "CANCELED": JobStatus.canceled,
    "CANCELLED": JobStatus.canceled,
}


class FalProvider:
    """fal.ai queue API provider adapter."""

    name = "fal"

    def __init__(self) -> None:
        self.api_key = os.getenv("FAL_API_KEY")
        self.base_url = os.getenv("FAL_QUEUE_BASE", "https://queue.fal.run").rstrip("/")
        self.timeout_seconds = float(os.getenv("FAL_TIMEOUT_SECONDS", "45"))

    async def submit(self, request: ProviderDispatchRequest) -> ProviderDispatchResult:
        self._assert_api_key()

        endpoint = f"{self.base_url}/{request.model_id}"
        payload = {
            "prompt": request.prompt,
            "image_url": str(request.image_url),
            "operation": request.operation.value,
            "tier": request.tier.value,
            "target_parts": [item.value for item in request.target_parts],
        }
        if request.mask_url:
            payload["mask_url"] = str(request.mask_url)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(endpoint, headers=self._headers(), json=payload)

        if response.status_code >= 400:
            detail = response.text[:240]
            raise RuntimeError(f"fal_submit_failed:{response.status_code}:{detail}")

        data = response.json()
        request_id = data.get("request_id") or data.get("requestId")
        if not request_id:
            raise RuntimeError("fal_submit_missing_request_id")

        return ProviderDispatchResult(
            provider_job_id=str(request_id),
            status=JobStatus.queued,
            estimated_cost_usd=self._estimate_cost_usd(request.model_id, request.tier),
        )

    async def get_status(self, provider_job_id: str, model_id: str) -> ProviderStatusResult:
        self._assert_api_key()

        status_endpoint = f"{self.base_url}/{model_id}/requests/{provider_job_id}/status"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            status_response = await client.get(status_endpoint, headers=self._headers())

        if status_response.status_code >= 400:
            detail = status_response.text[:240]
            raise RuntimeError(f"fal_status_failed:{status_response.status_code}:{detail}")

        status_data = status_response.json()
        raw_status = str(status_data.get("status", "")).upper()
        mapped_status = _FAL_STATUS_MAP.get(raw_status, JobStatus.failed)

        output_url: str | None = None
        error_code: str | None = None

        if mapped_status == JobStatus.completed:
            result_endpoint = f"{self.base_url}/{model_id}/requests/{provider_job_id}"
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                result_response = await client.get(result_endpoint, headers=self._headers())
            if result_response.status_code >= 400:
                detail = result_response.text[:240]
                raise RuntimeError(f"fal_result_failed:{result_response.status_code}:{detail}")
            output_url = self._extract_output_url(result_response.json())

        if mapped_status == JobStatus.failed:
            error_code = str(status_data.get("error", "provider_failed"))

        return ProviderStatusResult(status=mapped_status, output_url=output_url, error_code=error_code)

    async def cancel(self, provider_job_id: str, model_id: str) -> bool:
        self._assert_api_key()

        cancel_endpoint = f"{self.base_url}/{model_id}/requests/{provider_job_id}/cancel"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.put(cancel_endpoint, headers=self._headers())
        return response.status_code in {200, 202, 204}

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _assert_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("fal_api_key_missing")

    @staticmethod
    def _estimate_cost_usd(model_id: str, tier: RenderTier) -> float:
        model_key = model_id.lower()
        if "schnell" in model_key:
            return 0.005
        if "flux-2" in model_key or "flux-pro" in model_key:
            return 0.04 if tier == RenderTier.final else 0.01
        if "dev" in model_key:
            return 0.025
        return 0.02 if tier == RenderTier.preview else 0.04

    @classmethod
    def _extract_output_url(cls, data: dict[str, Any]) -> str | None:
        response_data = data.get("response", data)
        images = response_data.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                url = first.get("url")
                if isinstance(url, str):
                    return url

        output = response_data.get("output")
        if isinstance(output, dict):
            url = output.get("url")
            if isinstance(url, str):
                return url

        return cls._find_any_url(response_data)

    @classmethod
    def _find_any_url(cls, node: Any) -> str | None:
        if isinstance(node, dict):
            url_value = node.get("url")
            if isinstance(url_value, str) and url_value.startswith("http"):
                return url_value
            for value in node.values():
                nested = cls._find_any_url(value)
                if nested:
                    return nested
        if isinstance(node, list):
            for value in node:
                nested = cls._find_any_url(value)
                if nested:
                    return nested
        return None
