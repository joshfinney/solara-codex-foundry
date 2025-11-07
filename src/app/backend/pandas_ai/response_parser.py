"""Translate PandasAI response payloads into chat message blocks."""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from app.core.pandas_compat import pd
from app.models import chat as chat_models
from app.services.logging import StructuredLogger
from app.services.storage import ArtifactMetadata, StorageClient


@dataclass(slots=True)
class ParsedBlock:
    """Result of parsing a single PandasAI response fragment."""

    block: chat_models.MessageBlock
    attachments: List[ArtifactMetadata] = field(default_factory=list)


class PandasAIResponseParser:
    """Convert heterogeneous PandasAI payloads into message blocks."""

    def __init__(self, logger: StructuredLogger, storage: StorageClient, *, max_table_rows: int = 200) -> None:
        self._logger = logger
        self._storage = storage
        self._max_rows = max_table_rows

    # ------------------------------------------------------------------ public api
    def parse(self, payload: Any) -> List[ParsedBlock]:
        fragments = list(self._normalise_payload(payload))
        blocks: List[ParsedBlock] = []
        for fragment in fragments:
            block = self._parse_fragment(fragment)
            if block:
                blocks.append(block)
        if not blocks:
            text = json.dumps(payload, default=str)
            blocks.append(
                ParsedBlock(
                    block=chat_models.MessageBlock.single(
                        chat_models.MessagePart(kind="text", text=text)
                    )
                )
            )
        return blocks

    # ------------------------------------------------------------------ normalisation
    def _normalise_payload(self, payload: Any) -> Iterable[Dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, (list, tuple)):
            dicts: List[Dict[str, Any]] = []
            for item in payload:
                if isinstance(item, dict):
                    dicts.append(item)
                elif isinstance(item, str):
                    dicts.append({"type": "text", "value": item})
                else:
                    dicts.append({"type": "text", "value": json.dumps(item, default=str)})
            return dicts
        if isinstance(payload, str):
            return [{"type": "text", "value": payload}]
        if isinstance(payload, pd.DataFrame):
            return [{"type": "dataframe", "value": payload}]
        if hasattr(payload, "to_dict"):
            return [{"type": "object", "value": payload}]
        return [{"type": "text", "value": json.dumps(payload, default=str)}]

    # ------------------------------------------------------------------ fragment parsing
    def _parse_fragment(self, fragment: Dict[str, Any]) -> ParsedBlock | None:
        fragment_type = fragment.get("type") or fragment.get("response_type")
        if fragment_type == "text":
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="text", text=str(fragment.get("value") or ""))
                )
            )
        if fragment_type in {"markdown", "md"}:
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="text", text=str(fragment.get("value") or ""))
                )
            )
        if fragment_type in {"table", "dataframe"}:
            frame = fragment.get("value")
            if isinstance(frame, pd.DataFrame):
                rows = self._frame_to_records(frame)
            else:
                rows = self._coerce_records(fragment.get("value"))
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="table", table_rows=rows)
                )
            )
        if fragment_type == "plot":
            attachments: List[ArtifactMetadata] = []
            image_path = fragment.get("path") or fragment.get("image_path")
            image_b64 = fragment.get("base64") or fragment.get("image_base64")
            if image_path:
                attachments.append(self._upload_image_from_path(image_path))
            elif image_b64:
                attachments.append(self._upload_image_from_base64(image_b64, fragment))
            else:
                self._logger.warning("pandas_ai.plot.unavailable", fragment=str(fragment))
                return None
            image_url = attachments[0].object_key or image_path
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="image", image_path=image_url)
                ),
                attachments=attachments,
            )
        if fragment_type == "integer":
            try:
                value = int(fragment.get("value"))
            except Exception:  # noqa: BLE001
                value = 0
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="integer", integer_value=value)
                )
            )
        if fragment_type == "kv":
            pairs = fragment.get("value") or fragment.get("pairs") or []
            kv_pairs = self._coerce_pairs(pairs)
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="kv", kv_pairs=kv_pairs)
                )
            )
        if fragment_type == "object":
            value = fragment.get("value")
            text = json.dumps(value, default=str)
            return ParsedBlock(
                block=chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="text", text=text)
                )
            )
        # Fallback to text
        text_value = fragment.get("value")
        if isinstance(text_value, str):
            text = text_value
        else:
            text = json.dumps(text_value, default=str)
        return ParsedBlock(
            block=chat_models.MessageBlock.single(
                chat_models.MessagePart(kind="text", text=text)
            )
        )

    # ------------------------------------------------------------------ helpers
    def _upload_image_from_path(self, path_like: str) -> ArtifactMetadata:
        path = Path(path_like)
        name = f"pandasai/{path.name}"
        try:
            metadata = self._storage.upload_image_from_path(path, object_name=name)
        except FileNotFoundError:
            self._logger.error("pandas_ai.plot.missing", path=str(path))
            return ArtifactMetadata(name=path.name, content_type="", size=0, object_key=None)
        return metadata

    def _upload_image_from_base64(self, payload: str, fragment: Dict[str, Any]) -> ArtifactMetadata:
        try:
            data = base64.b64decode(payload)
        except Exception:  # noqa: BLE001
            self._logger.error("pandas_ai.plot.decode_error")
            return ArtifactMetadata(name="plot.png", content_type="image/png", size=0, object_key=None)
        object_name = fragment.get("name") or f"pandasai/{uuid.uuid4().hex}.png"
        metadata = self._storage.upload_artifact(
            name=object_name,
            content_type="image/png",
            data=data,
        )
        return metadata

    def _coerce_records(self, value: Any) -> Sequence[Dict[str, Any]]:
        if isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                return value[: self._max_rows]
            return [
                {"index": idx, "value": json.dumps(item, default=str)}
                for idx, item in enumerate(value[: self._max_rows])
            ]
        if isinstance(value, dict):
            return [value]
        if isinstance(value, pd.DataFrame):
            return self._frame_to_records(value)
        return [{"value": json.dumps(value, default=str)}]

    def _coerce_pairs(self, value: Any) -> Sequence[tuple[str, Any]]:
        if isinstance(value, dict):
            return list(value.items())
        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, dict):
                    result.extend(item.items())
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    result.append((str(item[0]), item[1]))
            return result
        return [("value", value)]

    def _frame_to_records(self, frame: pd.DataFrame) -> Sequence[Dict[str, Any]]:  # type: ignore[name-defined]
        if hasattr(frame, "head"):
            limited = frame.head(self._max_rows)
            if hasattr(limited, "to_dict"):
                try:
                    return limited.to_dict("records")
                except Exception:  # noqa: BLE001
                    pass
        if hasattr(frame, "to_dict"):
            try:
                records = frame.to_dict("records")
                return records[: self._max_rows]
            except Exception:  # noqa: BLE001
                pass
        return self._coerce_records(getattr(frame, "_records", []))
