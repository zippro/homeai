from __future__ import annotations

import base64
import os
from uuid import uuid4

import httpx

from app.schemas import (
    JobStatus,
    ProviderDispatchRequest,
    ProviderDispatchResult,
    ProviderStatusResult,
    RenderTier,
)
from app.storage import StorageUploader


class OpenAIProvider:
    """OpenAI image API adapter with storage-backed output handling."""

    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
        self.timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        self.return_stub_when_key_missing = os.getenv("OPENAI_STUB_IF_MISSING_KEY", "true").lower() == "true"
        self.storage = StorageUploader()

    async def submit(self, request: ProviderDispatchRequest) -> ProviderDispatchResult:
        if not self.api_key:
            if self.return_stub_when_key_missing:
                request_id = str(uuid4())
                return ProviderDispatchResult(
                    provider_job_id=request_id,
                    status=JobStatus.completed,
                    output_url=f"https://cdn.example.com/openai/{request_id}.jpg",
                    estimated_cost_usd=0.01 if request.tier == RenderTier.preview else 0.05,
                )
            raise RuntimeError("openai_api_key_missing")

        request_id = str(uuid4())
        output_url = await self._generate_or_edit(request)

        return ProviderDispatchResult(
            provider_job_id=request_id,
            status=JobStatus.completed,
            output_url=output_url,
            estimated_cost_usd=self._estimate_cost_usd(request.tier, request.model_id),
        )

    async def get_status(self, provider_job_id: str, model_id: str) -> ProviderStatusResult:
        # Submit path is synchronous currently.
        return ProviderStatusResult(
            status=JobStatus.completed,
            output_url=f"https://cdn.example.com/openai/{provider_job_id}.jpg",
        )

    async def cancel(self, provider_job_id: str, model_id: str) -> bool:
        # Synchronous request path cannot be canceled after submission.
        return False

    async def _generate_or_edit(self, request: ProviderDispatchRequest) -> str:
        image_bytes = await self._download_image_bytes(str(request.image_url))

        if image_bytes:
            edit_url = f"{self.base_url}/images/edits"
            files = {
                "image": ("image.png", image_bytes, "image/png"),
            }
            data = {
                "model": request.model_id,
                "prompt": request.prompt,
                "size": "1024x1024",
                "quality": "low" if request.tier == RenderTier.preview else "medium",
            }

            if request.mask_url:
                mask_bytes = await self._download_image_bytes(str(request.mask_url))
                if mask_bytes:
                    files["mask"] = ("mask.png", mask_bytes, "image/png")

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    edit_url,
                    headers=self._auth_headers(),
                    data=data,
                    files=files,
                )

            if response.status_code < 400:
                return await self._resolve_image_url(response.json())

        # Fallback to generation endpoint if edit path fails.
        generation_url = f"{self.base_url}/images/generations"
        payload = {
            "model": request.model_id,
            "prompt": request.prompt,
            "size": "1024x1024",
            "quality": "low" if request.tier == RenderTier.preview else "medium",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                generation_url,
                headers={**self._auth_headers(), "Content-Type": "application/json"},
                json=payload,
            )

        if response.status_code >= 400:
            detail = response.text[:240]
            raise RuntimeError(f"openai_image_failed:{response.status_code}:{detail}")

        return await self._resolve_image_url(response.json())

    async def _download_image_bytes(self, url: str) -> bytes | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
            if response.status_code >= 400:
                return None
            return response.content
        except Exception:  # noqa: BLE001
            return None

    async def _resolve_image_url(self, payload: dict) -> str:
        data = payload.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                maybe_url = first.get("url")
                if isinstance(maybe_url, str):
                    return maybe_url

                b64_json = first.get("b64_json")
                if isinstance(b64_json, str):
                    image_bytes = base64.b64decode(b64_json)
                    return await self.storage.upload_image_bytes(
                        image_bytes,
                        content_type="image/png",
                        key_prefix="openai",
                    )

        raise RuntimeError("openai_missing_output")

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    @staticmethod
    def _estimate_cost_usd(tier: RenderTier, model_id: str) -> float:
        model_key = model_id.lower()
        if "mini" in model_key:
            return 0.005 if tier == RenderTier.preview else 0.01
        return 0.01 if tier == RenderTier.preview else 0.05
