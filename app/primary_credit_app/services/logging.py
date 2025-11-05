"""Structured logging utilities with optional sinks."""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable


@dataclass
class LogEvent:
    """Structured payload emitted by the application."""

    event: str
    severity: str = "info"
    component: str = "primary-credit-app"
    message: str | None = None
    fields: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
            "event": self.event,
            "severity": self.severity,
            "component": self.component,
        }
        if self.message:
            payload["message"] = self.message
        if self.fields:
            payload.update(self.fields)
        return payload


class StructuredLogger:
    """Simple fan-out structured logger.

    The implementation writes to stdout by default and can be extended to
    additional sinks through environment configuration.
    """

    def __init__(self, name: str = "primary-credit") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
        self._console_enabled = os.getenv("PRIMARY_CREDIT_DISABLE_CONSOLE_LOGS", "0") != "1"
        self._opensearch_endpoint = os.getenv("PRIMARY_CREDIT_LOG_OPENSEARCH_URL")
        self._logstash_endpoint = os.getenv("PRIMARY_CREDIT_LOG_LOGSTASH_URL")

    def log(self, event: str, *, severity: str = "info", message: str | None = None, **fields: Any) -> None:
        payload = LogEvent(event=event, severity=severity, message=message, fields=fields)
        self._emit(payload)

    def info(self, event: str, **fields: Any) -> None:
        self.log(event, severity="info", **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.log(event, severity="warning", **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log(event, severity="error", **fields)

    # ------------------------------------------------------------------ internals
    def _emit(self, event: LogEvent) -> None:
        record = event.to_dict()
        if self._console_enabled:
            self._logger.info(json.dumps(record))
        for sink in self._iter_external_sinks():
            try:
                sink(record)
            except Exception:  # pragma: no cover - defensive
                self._logger.exception("Failed to emit structured log", extra={"event": record})

    def _iter_external_sinks(self) -> Iterable:
        if self._opensearch_endpoint:
            yield self._emit_opensearch
        if self._logstash_endpoint:
            yield self._emit_logstash

    def _emit_opensearch(self, payload: Dict[str, Any]) -> None:
        # In this environment we avoid performing network calls. Instead we log
        # a diagnostic entry that could be replaced with a real OpenSearch
        # client in production.
        self._logger.debug("[OpenSearch] %s", json.dumps(payload))

    def _emit_logstash(self, payload: Dict[str, Any]) -> None:
        self._logger.debug("[Logstash] %s", json.dumps(payload))
