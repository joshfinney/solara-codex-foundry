"""Test stub for ``solara.labs.headers`` helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    uid: str
    first_name: str
    last_name: Optional[str] = None
    display_name: Optional[str] = None


_default_user = User(uid="pc-tester", first_name="Test", last_name="User", display_name="Test User")


def use_user() -> User:
    """Return a static stub user."""

    return _default_user
