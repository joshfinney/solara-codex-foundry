"""Asynchronous chat backend backed by PandasAI."""

from __future__ import annotations

import asyncio
import io
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Sequence

from app.models import chat as chat_models
from app.services.logging import StructuredLogger
from app.services.storage import StorageClient
from app.services.telemetry import telemetry_span

from .progress import PipelineProgress
from .response_parser import PandasAIResponseParser


@dataclass(slots=True)
class PandasAIExecutionContext:
    """Holds context for a PandasAI execution request."""

    prompt: str
    conversation_id: str
    history: Sequence[chat_models.Message]


@dataclass(slots=True)
class PipelineResult:
    blocks: list[chat_models.MessageBlock]
    raw_response: Any
    python_code: str | None
    logs: str
    duration_ms: int


class PandasAIChatBackend:
    """Materialises the :class:`ChatBackend` protocol using PandasAI."""

    def __init__(
        self,
        pandas_ai_factory: Callable[[], Any],
        *,
        logger: StructuredLogger,
        storage: StorageClient,
        progress: PipelineProgress | None = None,
        response_parser: PandasAIResponseParser | None = None,
    ) -> None:
        self._pandas_ai_factory = pandas_ai_factory
        self._logger = logger
        self._progress = progress or PipelineProgress()
        self._parser = response_parser or PandasAIResponseParser(logger, storage)
        self._instance: Any | None = None

    # ------------------------------------------------------------------ public api
    async def respond(self, history: Sequence[chat_models.Message]) -> chat_models.Message:
        prompt = self._extract_latest_prompt(history)
        message_id = chat_models.new_message_id()
        context = PandasAIExecutionContext(prompt=prompt, conversation_id=message_id, history=history)
        await self._progress.publish("initialising PandasAI")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._run_pipeline, context)
        metadata = chat_models.MessageMetadata(
            python_code=result.python_code,
            source="pandas-ai",
            logs=result.logs or None,
        )
        blocks = result.blocks
        await self._progress.publish("response ready")
        return chat_models.Message(
            id=message_id,
            role="assistant",
            blocks=blocks,
            metadata=metadata,
            status="complete",
        )

    # ------------------------------------------------------------------ pipeline internals
    def _run_pipeline(self, context: PandasAIExecutionContext) -> PipelineResult:
        start_time = time.perf_counter()
        pandas_ai = self._ensure_instance()
        self._progress.publish_nowait("collecting context")
        with capture_logs("pandasai") as log_buffer:
            with telemetry_span(
                self._logger,
                "pandas_ai.chat",
                conversation_id=context.conversation_id,
            ):
                self._progress.publish_nowait("executing code")
                raw_response = self._invoke_chat(pandas_ai, context)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logs = log_buffer.getvalue()
        if logs:
            self._logger.info(
                "pandas_ai.chat.logs",
                conversation_id=context.conversation_id,
                logs=logs,
                event_type="ai_response_logs",
                event_data={"logs": logs},
            )
        blocks = [parsed.block for parsed in self._parser.parse(raw_response)]
        python_code = self._extract_last_code(pandas_ai)
        response_payload = self._serialise_blocks(blocks)
        event_data = {
            "response": response_payload,
            "last_code_executed": python_code,
            "elapsed_time_ms": duration_ms,
            "logs": logs or "",
        }
        self._logger.info(
            "pandas_ai.chat.audit",
            conversation_id=context.conversation_id,
            duration_ms=duration_ms,
            python_code=python_code,
            logs=logs or None,
            raw_response=self._serialise_raw_response(raw_response),
            event_type="ai_response",
            event_data=event_data,
        )
        self._logger.info(
            "pandas_ai.chat.complete",
            conversation_id=context.conversation_id,
            duration_ms=duration_ms,
            event_type="ai_response_complete",
            event_data={"duration_ms": duration_ms},
        )
        return PipelineResult(
            blocks=blocks,
            raw_response=raw_response,
            python_code=python_code,
            logs=logs,
            duration_ms=duration_ms,
        )

    def _invoke_chat(self, pandas_ai: Any, context: PandasAIExecutionContext) -> Any:
        if not hasattr(pandas_ai, "chat"):
            raise AttributeError("The provided PandasAI instance does not expose a chat method")
        prompt = context.prompt or ""
        try:
            response = pandas_ai.chat(prompt)
        finally:
            self._progress.publish_nowait("assembling response")
        return response

    def _ensure_instance(self) -> Any:
        if self._instance is None:
            self._instance = self._pandas_ai_factory()
        return self._instance

    def _extract_latest_prompt(self, history: Sequence[chat_models.Message]) -> str:
        for message in reversed(history):
            if message.role == "user":
                texts = [
                    part.text
                    for block in message.blocks
                    for part in block.parts
                    if part.kind == "text" and part.text
                ]
                return "\n\n".join(texts)
        return ""

    def _extract_last_code(self, pandas_ai: Any) -> str | None:
        candidate = getattr(pandas_ai, "last_code_executed", None)
        if candidate:
            return str(candidate)
        smart_dataframe = getattr(pandas_ai, "smart_dataframe", None)
        if smart_dataframe is None:
            smart_dataframe = getattr(pandas_ai, "_last_smart_dataframe", None)
        if smart_dataframe is None:
            return None
        agent = getattr(smart_dataframe, "agent", None) or getattr(smart_dataframe, "_agent", None)
        if agent is None:
            return None
        code = getattr(agent, "last_code_executed", None) or getattr(agent, "_last_code_executed", None)
        return str(code) if code else None

    def _serialise_blocks(self, blocks: Sequence[chat_models.MessageBlock]) -> list[dict[str, Any]]:
        serialised: list[dict[str, Any]] = []
        for block in blocks:
            parts: list[dict[str, Any]] = []
            for part in block.parts:
                payload: dict[str, Any] = {"kind": part.kind}
                if part.text is not None:
                    payload["text"] = part.text
                if part.image_path is not None:
                    payload["image_path"] = part.image_path
                if part.table_rows is not None:
                    payload["table_rows"] = [dict(row) for row in part.table_rows]
                if part.integer_value is not None:
                    payload["integer_value"] = part.integer_value
                if part.kv_pairs is not None:
                    payload["kv_pairs"] = [
                        {"key": key, "value": value} for key, value in part.kv_pairs
                    ]
                parts.append(payload)
            serialised.append({"parts": parts})
        return serialised

    @staticmethod
    def _serialise_raw_response(raw_response: Any) -> str:
        try:
            return str(raw_response)
        except Exception:  # pragma: no cover - defensive stringify
            return "<unserialisable>"


@contextmanager
def capture_logs(logger_name: str) -> Iterator[io.StringIO]:
    """Capture logging output from the specified logger into a buffer."""

    logger = logging.getLogger(logger_name)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        handler.close()
