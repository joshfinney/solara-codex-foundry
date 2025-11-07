"""Structured logging utilities with optional sinks."""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Sequence


@dataclass(slots=True)
class _LogContext:
    project_name: str
    environment: str
    region: str
    user_id: str | None
    page_type: str

    @classmethod
    def default_from_environment(cls) -> "_LogContext":
        project = os.getenv("PRIMARY_CREDIT_APP_NAME", "primary-credit")
        environment = os.getenv("PRIMARY_CREDIT_ENVIRONMENT_KEY", "local").lower()
        region = os.getenv("PRIMARY_CREDIT_REGION", "us-east-1").upper()
        user_id = os.getenv("PRIMARY_CREDIT_UID")
        return cls(project, environment, region, user_id, "new_issue")


class _Unset:
    pass


_UNSET = _Unset()


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
        self._console_format = os.getenv("PRIMARY_CREDIT_LOG_FORMAT", "human").lower()
        self._context = _LogContext.default_from_environment()
        endpoint = os.getenv("PRIMARY_CREDIT_LOG_LOGSTASH_URL")
        self._logstash_endpoints: tuple[str, ...] = (endpoint,) if endpoint else ()

    def log(self, event: str, *, severity: str = "info", message: str | None = None, **fields: Any) -> None:
        payload = LogEvent(event=event, severity=severity, message=message, fields=fields)
        self._emit(payload)

    def info(self, event: str, **fields: Any) -> None:
        self.log(event, severity="info", **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.log(event, severity="warning", **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log(event, severity="error", **fields)

    # ------------------------------------------------------------------ context configuration
    def configure_context(
        self,
        *,
        project_name: str | None = None,
        environment: str | None = None,
        region: str | None = None,
        user_id: str | None | _Unset = _UNSET,
        page_type: str | None = None,
    ) -> None:
        if project_name is not None:
            self._context.project_name = project_name
        if environment is not None:
            self._context.environment = environment.lower()
        if region is not None:
            self._context.region = region.upper()
        if user_id is not _UNSET:
            self._context.user_id = user_id
        if page_type is not None:
            self._context.page_type = page_type

    def configure_logstash_endpoints(self, endpoints: Sequence[str]) -> None:
        unique: list[str] = []
        for endpoint in endpoints:
            trimmed = endpoint.strip()
            if not trimmed:
                continue
            if trimmed not in unique:
                unique.append(trimmed)
        self._logstash_endpoints = tuple(unique)
        if self._logstash_endpoints:
            self._logger.setLevel(min(self._logger.level, logging.DEBUG))

    def set_page_type(self, page_type: str) -> None:
        self._context.page_type = page_type

    def set_user_id(self, user_id: str | None) -> None:
        self._context.user_id = user_id

    # ------------------------------------------------------------------ internals
    def _emit(self, event: LogEvent) -> None:
        record = event.to_dict()
        if self._console_enabled:
            self._emit_console(record)
        for sink in self._iter_external_sinks():
            try:
                sink(dict(record))
            except Exception:  # pragma: no cover - defensive
                self._logger.exception("Failed to emit structured log", extra={"event": record})

    # ------------------------------------------------------------------ formatting helpers
    def _emit_console(self, record: Dict[str, Any]) -> None:
        fmt = self._console_format
        level = self._severity_to_level(record.get("severity", "info"))
        if fmt in {"json", "both"}:
            self._logger.log(level, json.dumps(record))
        if fmt in {"human", "both"}:
            human = self._format_human(record)
            self._logger.log(level, human)

    def _iter_external_sinks(self) -> Iterable[Callable[[Dict[str, Any]], None]]:
        for endpoint in self._logstash_endpoints:
            yield lambda payload, endpoint=endpoint: self._emit_logstash(endpoint, payload)

    @staticmethod
    def _severity_to_level(severity: str) -> int:
        mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        return mapping.get(severity.lower(), logging.INFO)

    def _format_human(self, record: Dict[str, Any]) -> str:
        data = dict(record)
        timestamp = data.pop("timestamp", "-")
        event = data.pop("event", "unknown")
        severity = data.pop("severity", "info").upper()
        component = data.pop("component", "")
        message = data.pop("message", None)
        fields = " ".join(
            f"{key}={self._format_field_value(value)}" for key, value in sorted(data.items())
        )
        parts = [f"[{timestamp}]", severity, event]
        if component:
            parts.append(f"({component})")
        if message:
            parts.append(f"- {message}")
        if fields:
            parts.append(f"- {fields}")
        return " ".join(part for part in parts if part)

    @staticmethod
    def _format_field_value(value: Any) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    def _emit_logstash(self, endpoint: str, payload: Dict[str, Any]) -> None:
        record = dict(payload)
        event_type = record.pop("event_type", record.get("event"))
        page_type = record.pop("page_type", self._context.page_type)
        conversation_id = record.get("conversation_id")
        user_id = record.pop("user_id", self._context.user_id)
        event_data = record.pop("event_data", None)
        ignore_keys = {"timestamp", "event", "severity", "component", "message"}
        if event_data is None:
            event_data = {key: value for key, value in record.items() if key not in ignore_keys}
        body = {
            "project_name": self._context.project_name,
            "environment": self._context.environment,
            "region": self._context.region,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "event_type": event_type,
            "page_type": page_type,
            "event_data": event_data,
        }
        self._logger.debug("[Logstash:%s] %s", endpoint, json.dumps(body, default=str))
