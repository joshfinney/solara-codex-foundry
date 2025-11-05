"""Utility to provide pandas or the local stub when unavailable."""

from __future__ import annotations

try:  # pragma: no cover - prefer real pandas
    import pandas as pd  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - test fallback
    from . import pandas_stub as pd  # type: ignore

__all__ = ["pd"]
