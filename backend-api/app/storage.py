from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError


@dataclass
class StorageConfig:
    bucket: str | None
    region: str | None
    endpoint_url: str | None
    access_key_id: str | None
    secret_access_key: str | None
    public_base_url: str | None


class StorageUploader:
    """Uploads generated images to S3-compatible object storage."""

    def __init__(self) -> None:
        self.config = StorageConfig(
            bucket=os.getenv("STORAGE_BUCKET"),
            region=os.getenv("STORAGE_REGION", "us-east-1"),
            endpoint_url=os.getenv("STORAGE_ENDPOINT_URL"),
            access_key_id=os.getenv("STORAGE_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("STORAGE_SECRET_ACCESS_KEY"),
            public_base_url=os.getenv("STORAGE_PUBLIC_BASE_URL"),
        )
        self._client = None

    async def upload_image_bytes(
        self,
        data: bytes,
        *,
        content_type: str = "image/png",
        key_prefix: str = "openai",
    ) -> str:
        return await asyncio.to_thread(
            self._upload_image_bytes_sync,
            data,
            content_type,
            key_prefix,
        )

    def _upload_image_bytes_sync(self, data: bytes, content_type: str, key_prefix: str) -> str:
        client = self._get_client()
        key = self._build_object_key(key_prefix)

        try:
            client.upload_fileobj(
                Fileobj=BytesIO(data),
                Bucket=self.config.bucket,
                Key=key,
                ExtraArgs={"ContentType": content_type},
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"storage_upload_failed:{exc}") from exc

        return self._build_public_url(key)

    def _get_client(self):
        if not self.config.bucket:
            raise RuntimeError("storage_bucket_missing")

        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name=self.config.region,
            )
        return self._client

    def _build_object_key(self, key_prefix: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d/%H%M%S")
        return f"{key_prefix}/{timestamp}_{uuid4().hex}.png"

    def _build_public_url(self, key: str) -> str:
        if self.config.public_base_url:
            base = self.config.public_base_url.rstrip("/")
            return f"{base}/{key}"

        if self.config.endpoint_url:
            endpoint = self.config.endpoint_url.rstrip("/")
            return f"{endpoint}/{self.config.bucket}/{key}"

        region = self.config.region or "us-east-1"
        return f"https://{self.config.bucket}.s3.{region}.amazonaws.com/{key}"
