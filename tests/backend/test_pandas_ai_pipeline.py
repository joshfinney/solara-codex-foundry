from __future__ import annotations

import asyncio
import logging

from app.backend.pandas_ai.pipeline import PandasAIChatBackend
from app.backend.pandas_ai.progress import PipelineProgress
from app.backend.pandas_ai.response_parser import PandasAIResponseParser
from app.models import chat as chat_models


class StubLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def info(self, event: str, **fields):
        self.events.append((event, fields))

    warning = error = info


class StubStorage:
    def upload_artifact(self, *, name: str, content_type: str, data: bytes):
        return type("Meta", (), {"name": name, "content_type": content_type, "size": len(data), "object_key": name})()

    def upload_image_from_path(self, path, *, object_name: str | None = None, content_type: str | None = None):
        return type("Meta", (), {"name": object_name or str(path), "content_type": content_type or "image/png", "size": 0, "object_key": object_name or str(path)})()


class DummyPandasAI:
    def __init__(self) -> None:
        self.smart_dataframe = type("SmartDataFrame", (), {"agent": type("Agent", (), {"last_code_executed": "print('hi')"})()})()

    def chat(self, prompt: str):
        logging.getLogger("pandasai").info("executing", extra={"prompt": prompt})
        return [
            {"type": "text", "value": f"Answer for {prompt}"},
            {"type": "integer", "value": 3},
        ]


def test_pipeline_returns_message(tmp_path):
    logger = StubLogger()
    storage = StubStorage()
    parser = PandasAIResponseParser(logger, storage)
    progress = PipelineProgress()
    backend = PandasAIChatBackend(
        lambda: DummyPandasAI(),
        logger=logger,
        storage=storage,
        progress=progress,
        response_parser=parser,
    )

    user_message = chat_models.Message(
        id="user-1",
        role="user",
        blocks=[
            chat_models.MessageBlock.single(
                chat_models.MessagePart(kind="text", text="Show the latest figures")
            )
        ],
    )

    response = asyncio.run(backend.respond([user_message]))
    assert response.role == "assistant"
    assert response.metadata.python_code == "print('hi')"
    assert response.metadata.logs and "executing" in response.metadata.logs
    audit_events = [fields for event, fields in logger.events if event == "pandas_ai.chat.audit"]
    assert audit_events, "expected audit telemetry to be emitted"
    audit_payload = audit_events[-1]
    assert audit_payload["python_code"] == "print('hi')"
    assert audit_payload["event_type"] == "ai_response"
    event_data = audit_payload["event_data"]
    assert event_data["last_code_executed"] == "print('hi')"
    assert "executing" in event_data["logs"]
    assert event_data["response"][0]["parts"][0]["kind"] == "text"
    assert any(event == "pandas_ai.chat.complete" for event, _ in logger.events)
    assert progress.latest_stage == "response ready"
    parts = [part for block in response.blocks for part in block.parts]
    kinds = [part.kind for part in parts]
    assert kinds == ["text", "integer"]
