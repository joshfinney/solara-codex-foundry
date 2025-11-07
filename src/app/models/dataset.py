"""Data contracts shared between services and application state."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict


@dataclass(slots=True)
class BootstrapResult:
    """Result of the initial bootstrap handshake."""

    config: "QRExecConfig"
    credentials: "RuntimeCredentials"
    storage: "StorageCredentials | None" = None
    llm: "LLMParameters | None" = None
    embeddings: "EmbeddingParameters | None" = None

    def public_config(self) -> Dict[str, str]:
        return self.credentials.public_config()


@dataclass(slots=True)
class DatasetResult:
    """Canonical representation of the loaded issuance dataset."""

    rows: list[dict[str, Any]]
    frame: "pd.DataFrame | None"
    source: str
    loaded_at: _dt.datetime
    earliest_issue_date: _dt.date
    latest_issue_date: _dt.date

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def max_window_days(self) -> int:
        return (self.latest_issue_date - self.earliest_issue_date).days + 1


@dataclass(slots=True)
class FilterResult:
    """Result of applying a rolling window filter to the dataset."""

    window_days: int
    rows: list[dict[str, Any]]
    frame: "pd.DataFrame | None"
    row_count: int
    duration_ms: int
    cache_hit: bool = False


@dataclass(slots=True)
class InlineFeedback:
    """Record submitted from the inline feedback panel."""

    conversation_id: str
    comments: str
    submitted_at: _dt.datetime = field(
        default_factory=lambda: _dt.datetime.now(_dt.timezone.utc)
    )


if TYPE_CHECKING:  # pragma: no cover - mypy only
    from app.services.credentials import (
        EmbeddingParameters,
        LLMParameters,
        QRExecConfig,
        RuntimeCredentials,
        StorageCredentials,
    )
    import pandas as pd  # type: ignore
else:  # pragma: no cover - runtime safe fallbacks
    EmbeddingParameters = "EmbeddingParameters"  # type: ignore[valid-type]
    LLMParameters = "LLMParameters"  # type: ignore[valid-type]
    QRExecConfig = "QRExecConfig"  # type: ignore[valid-type]
    RuntimeCredentials = "RuntimeCredentials"  # type: ignore[valid-type]
    StorageCredentials = "StorageCredentials"  # type: ignore[valid-type]
    pd = None  # type: ignore

