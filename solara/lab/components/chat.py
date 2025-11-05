"""Minimal stub for Solara lab chat message."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def ChatMessage(*args, **kwargs) -> Iterator[None]:
    yield None
