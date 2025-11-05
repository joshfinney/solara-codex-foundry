"""Storage helpers for S3 interactions and artifact persistence."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core import optional_dependencies
from .logging import StructuredLogger


@dataclass
class ArtifactMetadata:
    name: str
    content_type: str
    size: int
    object_key: str | None = None


class StorageClient:
    """Thin wrapper over boto3 to isolate the dependency surface."""

    def __init__(self, logger: StructuredLogger, bucket: str | None = None, prefix: str = "artifacts/") -> None:
        self._logger = logger
        self._bucket = bucket
        self._prefix = prefix.strip("/") + "/" if prefix else ""
        self._s3 = None
        if bucket and optional_dependencies.is_boto3_available():  # pragma: no branch - simple guard
            import boto3  # type: ignore

            self._s3 = boto3.client("s3")
            self._logger.info("storage.s3.initialized", bucket=bucket)
        else:
            if bucket:
                self._logger.warning("storage.s3.unavailable", reason="boto3 not installed")

    # ------------------------------------------------------------------ parquet loading
    def read_parquet(self, key: str) -> bytes | None:
        if not self._bucket or not self._s3:
            self._logger.warning("storage.s3.disabled", bucket=self._bucket)
            return None
        self._logger.info("storage.s3.read_parquet", bucket=self._bucket, key=key)
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        except Exception as error:  # noqa: BLE001
            self._logger.error("storage.s3.read_failed", bucket=self._bucket, key=key, error=str(error))
            return None
        body: bytes = obj["Body"].read()
        return body

    # ------------------------------------------------------------------ artifact upload
    def upload_artifact(self, *, name: str, content_type: str, data: bytes) -> ArtifactMetadata:
        size = len(data)
        object_key = None
        if self._bucket and self._s3:
            object_key = f"{self._prefix}{name}"
            try:
                self._s3.put_object(Bucket=self._bucket, Key=object_key, Body=data, ContentType=content_type)
                self._logger.info(
                    "storage.s3.upload_success",
                    bucket=self._bucket,
                    key=object_key,
                    size=size,
                    content_type=content_type,
                )
            except Exception as error:  # noqa: BLE001
                self._logger.error(
                    "storage.s3.upload_failed",
                    bucket=self._bucket,
                    key=object_key,
                    error=str(error),
                )
                object_key = None
        else:
            self._logger.info("storage.s3.upload_skipped", reason="bucket or boto3 missing")
        return ArtifactMetadata(name=name, content_type=content_type, size=size, object_key=object_key)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def decode_base64_payload(value: str) -> bytes:
        try:
            return base64.b64decode(value)
        except Exception as error:  # noqa: BLE001
            raise ValueError("Invalid base64 payload") from error

    def upload_base64_artifact(self, *, name: str, content_type: str, payload: str) -> ArtifactMetadata:
        data = self.decode_base64_payload(payload)
        return self.upload_artifact(name=name, content_type=content_type, data=data)
