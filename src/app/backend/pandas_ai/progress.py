"""Lightweight publisher for long-running PandasAI executions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import List, Optional


@dataclass
class PipelineProgress:
    """Holds the most recent stage label and notifies subscribers."""

    initial_stage: str = "initialising"
    _subscribers: List[Callable[[str], None]] = field(default_factory=list, init=False)
    _latest_stage: str = field(default="initialising", init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self._latest_stage = self.initial_stage

    async def publish(self, stage: str) -> None:
        self.publish_nowait(stage)

    def publish_nowait(self, stage: str) -> None:
        with self._lock:
            self._latest_stage = stage
            for callback in list(self._subscribers):
                try:
                    callback(stage)
                except Exception:  # pragma: no cover - notification guard
                    pass

    def subscribe(self, callback: Callable[[str], None], *, replay_last: bool = True) -> None:
        with self._lock:
            self._subscribers.append(callback)
            last = self._latest_stage
        if replay_last and last:
            callback(last)

    @property
    def latest_stage(self) -> str:
        return self._latest_stage

    async def reset(self, stage: Optional[str] = None) -> None:
        await self.publish(stage or self.initial_stage)
