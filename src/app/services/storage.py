"""Storage helpers for S3FS interactions and artifact persistence."""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

from app.core.pandas_compat import pd
from app.core import pandas_stub

from .credentials import StorageCredentials
from .logging import StructuredLogger


@dataclass(slots=True)
class ArtifactMetadata:
    name: str
    content_type: str
    size: int
    object_key: str | None = None


class StorageClient:
    """Thin wrapper over S3FS to isolate the dependency surface."""

    def __init__(
        self,
        logger: StructuredLogger,
        *,
        credentials: StorageCredentials | None = None,
        filesystem: Any | None = None,
    ) -> None:
        self._logger = logger
        self._credentials: StorageCredentials | None = None
        self._fs: Any | None = filesystem
        self._scheme = "s3"
        self._prefix = ""
        if credentials:
            self.configure(credentials, filesystem=filesystem)

    # ------------------------------------------------------------------ configuration
    def configure(
        self,
        credentials: StorageCredentials,
        *,
        filesystem: Any | None = None,
    ) -> None:
        self._credentials = credentials
        self._scheme = credentials.scheme or "s3"
        self._prefix = credentials.prefix.strip("/")
        if self._prefix:
            self._prefix += "/"
        self._fs = filesystem or self._build_filesystem(credentials)
        self._logger.info(
            "storage.configured",
            bucket=credentials.bucket,
            scheme=self._scheme,
            prefix=self._prefix,
        )

    def _build_filesystem(self, credentials: StorageCredentials):  # type: ignore[no-untyped-def]
        if self._scheme != "s3":
            try:
                import fsspec
            except ImportError as error:  # pragma: no cover - import guard
                raise RuntimeError("Filesystem backend unavailable") from error
            return fsspec.filesystem(self._scheme)

        try:
            import s3fs
        except Exception as error:  # noqa: BLE001 - dependency guard
            self._logger.error("storage.s3fs.unavailable", error=str(error))
            raise

        fs_kwargs: dict[str, Any] = {
            "anon": credentials.anonymous,
            "use_listings_cache": credentials.use_listings_cache,
        }
        if credentials.key:
            fs_kwargs["key"] = credentials.key
        if credentials.secret:
            fs_kwargs["secret"] = credentials.secret
        if credentials.client_kwargs:
            fs_kwargs["client_kwargs"] = credentials.client_kwargs
        if credentials.s3_additional_kwargs:
            fs_kwargs["s3_additional_kwargs"] = credentials.s3_additional_kwargs
        return s3fs.S3FileSystem(**fs_kwargs)

    # ------------------------------------------------------------------ dataset loading
    def read_table(self, key: str) -> Tuple[pd.DataFrame | None, str]:
        if not self._ready:
            self._logger.warning("storage.unconfigured", key=key)
            return None, ""
        uri, object_key = self._make_uri(key)
        format_name = self._infer_format(object_key)
        loader = self._resolve_loader(format_name)
        try:
            with self._fs.open(uri, "rb") as handle:
                frame = loader(handle)
        except FileNotFoundError:
            raise
        except Exception as error:  # noqa: BLE001
            self._logger.error("storage.read_table.failed", key=object_key, error=str(error))
            return None, format_name
        row_count = self._resolve_row_count(frame)
        self._logger.info(
            "storage.read_table.success",
            key=object_key,
            format=format_name,
            rows=row_count,
        )
        return frame, format_name

    def read_parquet(self, key: str):  # type: ignore[no-untyped-def]
        frame, format_name = self.read_table(key)
        if frame is not None and format_name != "parquet":
            self._logger.warning("storage.read_parquet.mismatch", key=key, format=format_name)
        return frame

    def read_csv(self, key: str):  # type: ignore[no-untyped-def]
        frame, format_name = self.read_table(key)
        if frame is not None and format_name != "csv":
            self._logger.warning("storage.read_csv.mismatch", key=key, format=format_name)
        return frame

    # ------------------------------------------------------------------ artifact upload / download
    def upload_artifact(self, *, name: str, content_type: str, data: bytes) -> ArtifactMetadata:
        size = len(data)
        object_key = None
        if not self._ready:
            self._logger.warning("storage.upload_skipped", reason="client not configured")
            return ArtifactMetadata(name=name, content_type=content_type, size=size, object_key=object_key)

        key = self._build_prefixed_key(name)
        uri, object_key = self._make_uri(key)
        extra_kwargs = dict(self._credentials.s3_additional_kwargs) if self._credentials else {}
        if content_type:
            extra_kwargs.setdefault("ContentType", content_type)
        try:
            if hasattr(self._fs, "pipe"):
                self._fs.pipe(uri, data, **extra_kwargs)
            else:  # pragma: no cover - exercised in non S3 filesystems
                with self._fs.open(uri, "wb") as handle:
                    handle.write(data)
        except Exception as error:  # noqa: BLE001
            self._logger.error("storage.upload_failed", key=object_key, error=str(error))
            object_key = None
        else:
            self._logger.info(
                "storage.upload_success",
                key=object_key,
                size=size,
                content_type=content_type,
            )
        return ArtifactMetadata(name=name, content_type=content_type, size=size, object_key=object_key)

    def upload_image_from_path(
        self,
        path: Path,
        *,
        object_name: str | None = None,
        content_type: str | None = None,
    ) -> ArtifactMetadata:
        name = object_name or path.name
        guessed_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        return self.upload_artifact(name=name, content_type=guessed_type, data=data)

    def download_image(self, key: str) -> bytes | None:
        try:
            return self.read_bytes(key)
        except FileNotFoundError:
            self._logger.error("storage.download_missing", key=key)
            return None

    def read_bytes(self, key: str) -> bytes:
        if not self._ready:
            self._logger.warning("storage.unconfigured", key=key)
            return b""
        uri, object_key = self._make_uri(key)
        try:
            with self._fs.open(uri, "rb") as handle:
                payload = handle.read()
        except FileNotFoundError:
            raise
        except Exception as error:  # noqa: BLE001
            self._logger.error("storage.read_bytes.failed", key=object_key, error=str(error))
            return b""
        self._logger.info("storage.read_bytes.success", key=object_key, size=len(payload))
        return payload

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

    # ------------------------------------------------------------------ internal utilities
    @property
    def _ready(self) -> bool:
        return self._credentials is not None and self._fs is not None

    def _make_uri(self, key: str) -> Tuple[str, str]:
        if self._credentials is None:
            raise RuntimeError("Storage client not configured")
        if key.startswith(f"{self._scheme}://"):
            return key, key.split("//", 1)[1]
        object_key = key.lstrip("/")
        uri = f"{self._scheme}://{self._credentials.bucket}/{object_key}"
        return uri, object_key

    def _build_prefixed_key(self, name: str) -> str:
        return f"{self._prefix}{name}" if self._prefix else name

    @staticmethod
    def _infer_format(key: str) -> str:
        lowered = key.lower()
        if lowered.endswith(".parquet"):
            return "parquet"
        if lowered.endswith(".csv"):
            return "csv"
        return "parquet"

    def _resolve_loader(self, format_name: str):  # type: ignore[no-untyped-def]
        if format_name == "csv":
            if hasattr(pd, "read_csv"):
                return pd.read_csv
            return self._read_csv_fallback
        if hasattr(pd, "read_parquet"):
            return pd.read_parquet
        return self._read_parquet_fallback

    @staticmethod
    def _resolve_row_count(frame) -> int:  # type: ignore[no-untyped-def]
        try:
            return len(frame)  # type: ignore[arg-type]
        except TypeError:
            pass
        if hasattr(frame, "to_dict"):
            try:
                records = frame.to_dict("records")
                return len(records)
            except Exception:  # noqa: BLE001
                return 0
        return 0

    @staticmethod
    def _read_csv_fallback(handle):  # type: ignore[no-untyped-def]
        content = handle.read()
        if isinstance(content, bytes):
            content = content.decode()
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return pandas_stub.DataFrame([])
        headers = [part.strip() for part in lines[0].split(",")]
        rows = []
        for line in lines[1:]:
            values = [part.strip() for part in line.split(",")]
            rows.append(dict(zip(headers, values)))
        return pandas_stub.DataFrame(rows)

    @staticmethod
    def _read_parquet_fallback(handle):  # type: ignore[no-untyped-def]
        raise RuntimeError("Parquet support requires pandas")

