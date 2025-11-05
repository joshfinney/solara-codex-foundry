"""Feature flag helpers for optional third-party dependencies."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=None)
def is_pandas_available() -> bool:
    try:  # pragma: no cover - import guard
        import pandas  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


@lru_cache(maxsize=None)
def is_ipyaggrid_available() -> bool:
    try:  # pragma: no cover - import guard
        import ipyaggrid  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


@lru_cache(maxsize=None)
def is_boto3_available() -> bool:
    try:  # pragma: no cover - import guard
        import boto3  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True
