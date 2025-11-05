"""Observability primitives for instrumentation within the app."""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional

from .logging import StructuredLogger


@dataclass
class TelemetrySpan:
    """Data captured for a single span."""

    name: str
    start_time: float
    metadata: Dict[str, Any]


@contextlib.contextmanager
def telemetry_span(logger: StructuredLogger, name: str, **metadata: Any) -> Iterator[TelemetrySpan]:
    """Context manager that logs span lifecycle events."""

    start = time.perf_counter()
    logger.info("telemetry.span.start", span=name, **metadata)
    span = TelemetrySpan(name=name, start_time=start, metadata=metadata)
    try:
        yield span
    except Exception as error:
        logger.error("telemetry.span.error", span=name, error=str(error), **metadata)
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("telemetry.span.finish", span=name, duration_ms=duration_ms, **metadata)


class SpanTicker:
    """Produces stage labels while a long-running task is active."""

    def __init__(self, stages: Optional[list[str]] = None, interval_seconds: float = 2.0) -> None:
        self.stages = stages or [
            "Validating prompt",
            "Gathering context",
            "Running PandasAI transforms",
            "Drafting response",
        ]
        self.interval_seconds = interval_seconds
        self._index = 0
        self._last_tick = time.perf_counter()

    def current_label(self) -> str:
        now = time.perf_counter()
        if now - self._last_tick >= self.interval_seconds:
            self._index = (self._index + 1) % len(self.stages)
            self._last_tick = now
        return self.stages[self._index]

    def reset(self) -> None:
        self._index = 0
        self._last_tick = time.perf_counter()
