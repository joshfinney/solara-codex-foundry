"""Minimal stub of ipyaggrid for tests."""

from __future__ import annotations

from typing import Any, Dict


class Grid:
    def __init__(self, grid_data: Any, grid_options: Dict[str, Any] | None = None, **_kwargs) -> None:
        self.grid_data = grid_data
        self.grid_options = grid_options or {}

    def _repr_html_(self) -> str:
        return "<div class='ag-grid-stub'>Grid preview unavailable in tests.</div>"
