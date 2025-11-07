import base64
import io

from app.services.credentials import StorageCredentials
from app.services.logging import StructuredLogger
from app.services.storage import StorageClient


class MemoryFS:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def pipe(self, uri: str, data: bytes, **_: object) -> None:
        self.store[self._strip(uri)] = data

    def open(self, uri: str, mode: str):  # type: ignore[no-untyped-def]
        path = self._strip(uri)
        if "r" in mode:
            if path not in self.store:
                raise FileNotFoundError(path)
            return io.BytesIO(self.store[path])
        return _MemoryWriter(self.store, path)

    @staticmethod
    def _strip(uri: str) -> str:
        return uri.split("://", 1)[1] if "://" in uri else uri


class _MemoryWriter(io.BytesIO):
    def __init__(self, store: dict[str, bytes], path: str) -> None:
        super().__init__()
        self._store = store
        self._path = path

    def close(self) -> None:  # pragma: no cover - exercised indirectly
        self._store[self._path] = self.getvalue()
        super().close()


def test_storage_read_and_image_roundtrip(tmp_path):
    fs = MemoryFS()
    logger = StructuredLogger("test-storage")
    creds = StorageCredentials(
        bucket="test-bucket",
        dataset_key="datasets/sample.csv",
        prefix="artifacts/",
        scheme="memory",
        anonymous=True,
        client_kwargs={},
        s3_additional_kwargs={},
        use_listings_cache=False,
    )

    storage = StorageClient(logger, filesystem=fs)
    storage.configure(creds, filesystem=fs)

    csv_bytes = b"issue_date,cusip\n2024-01-01,12345\n"
    fs.store["test-bucket/datasets/sample.csv"] = csv_bytes

    table, format_name = storage.read_table("datasets/sample.csv")
    assert format_name == "csv"
    assert table.to_dict("records")[0]["cusip"] == "12345"

    image_path = tmp_path / "chart.png"
    image_bytes = b"binary-image"
    image_path.write_bytes(image_bytes)

    metadata = storage.upload_image_from_path(image_path)
    assert metadata.object_key == "artifacts/chart.png"
    assert fs.store["test-bucket/" + metadata.object_key] == image_bytes

    downloaded = storage.download_image(metadata.object_key)
    assert downloaded == image_bytes

    payload = base64.b64encode(b"hello").decode()
    meta = storage.upload_base64_artifact(name="greeting.txt", content_type="text/plain", payload=payload)
    assert meta.object_key == "artifacts/greeting.txt"
