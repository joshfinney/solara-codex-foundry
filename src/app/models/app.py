"""Application-level state containers shared across the UI."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.models import dataset as dataset_models


@dataclass(slots=True)
class GateState:
    """Minimal state required for the login/attestation flow."""

    is_authenticated: bool = False
    has_accepted_terms: bool = False
    username: Optional[str] = None
    attestation_message: str = (
        "I confirm that I will validate AI output before using it for credit decisions."
    )


@dataclass(slots=True)
class SessionState:
    bootstrapping: bool = False
    ready: bool = False
    error: str | None = None
    loading_label: str = "Preparing workspace…"
    celery_ready: bool = False
    public_config: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DatasetState:
    raw: dataset_models.DatasetResult | None = None
    filtered: dataset_models.FilterResult | None = None
    cache: Dict[int, dataset_models.FilterResult] = field(default_factory=dict)
    lookback_days: int = 14
    max_lookback_days: int = 60
    cache_hits: int = 0
    cache_misses: int = 0
    last_duration_ms: int | None = None
    last_cache_hit: bool = False


@dataclass(slots=True)
class UIState:
    sidebar_open: bool = False
    active_tab: str = "new_issues"
    inline_feedback_text: str = ""
    inline_feedback_status: str = "idle"
    conversation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


@dataclass(slots=True)
class AppState:
    gate: GateState = field(default_factory=GateState)
    session: SessionState = field(default_factory=SessionState)
    dataset: DatasetState = field(default_factory=DatasetState)
    ui: UIState = field(default_factory=UIState)

