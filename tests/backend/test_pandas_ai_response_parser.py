from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.backend.pandas_ai.response_parser import PandasAIResponseParser
from app.core.pandas_compat import pd


class StubLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def info(self, event: str, **fields):
        self.events.append((event, fields))

    warning = error = info


class StubStorage:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.uploaded: list[tuple[str, bytes]] = []

    def upload_artifact(self, *, name: str, content_type: str, data: bytes):
        self.uploaded.append((name, data))
        return type("Meta", (), {"name": name, "content_type": content_type, "size": len(data), "object_key": name})()

    def upload_image_from_path(self, path: Path, *, object_name: str | None = None, content_type: str | None = None):
        data = path.read_bytes()
        name = object_name or path.name
        self.uploaded.append((name, data))
        return type("Meta", (), {"name": name, "content_type": content_type or "image/png", "size": len(data), "object_key": name})()


@pytest.fixture
def parser(tmp_path):
    logger = StubLogger()
    storage = StubStorage(tmp_path)
    return PandasAIResponseParser(logger, storage)


def test_parse_text(parser):
    blocks = parser.parse({"type": "text", "value": "hello"})
    assert len(blocks) == 1
    part = blocks[0].block.parts[0]
    assert part.kind == "text"
    assert part.text == "hello"


def test_parse_dataframe(parser):
    frame = pd.DataFrame([{"a": 1}, {"a": 2}])
    blocks = parser.parse({"type": "dataframe", "value": frame})
    table = blocks[0].block.parts[0]
    assert table.kind == "table"
    assert table.table_rows == [{"a": 1}, {"a": 2}]


def test_parse_plot_base64(parser, tmp_path):
    image_path = tmp_path / "plot.png"
    image_path.write_bytes(b"fake-image")
    payload = base64.b64encode(b"fake-image").decode("ascii")
    blocks = parser.parse({"type": "plot", "base64": payload, "name": "plot.png"})
    assert blocks[0].block.parts[0].kind == "image"
    assert parser._storage.uploaded  # type: ignore[attr-defined]
