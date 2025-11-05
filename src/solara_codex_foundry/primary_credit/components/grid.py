"""Issuance grid with optional Ag-Grid support."""

from __future__ import annotations

import html
from typing import Iterable

import solara

from ..core import optional_dependencies
from ..core.state import AppController


def _render_table(rows: Iterable[dict]) -> str:
    headers = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(key)
    header_html = "".join(f"<th>{html.escape(str(col))}</th>" for col in headers)
    body_html = ""
    for row in rows:
        body_html += "<tr>"
        for col in headers:
            body_html += f"<td>{html.escape(str(row.get(col, '')))}</td>"
        body_html += "</tr>"
    return f"<table class='pc-table'><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"


@solara.component
def IssueGrid(controller: AppController):
    dataset_state = controller.state.use(lambda s: s.dataset)
    filtered = dataset_state.filtered
    rows = filtered.rows if filtered else (dataset_state.raw.rows if dataset_state.raw else [])
    frame = filtered.frame if filtered and filtered.frame is not None else (
        dataset_state.raw.frame if dataset_state.raw else None
    )

    prefer_aggrid = optional_dependencies.is_ipyaggrid_available() and optional_dependencies.is_pandas_available()
    if prefer_aggrid and frame is not None:
        try:
            from ipyaggrid import Grid  # type: ignore

            grid = Grid(grid_data=frame, quick_filter=True)
            if hasattr(solara, "display"):
                solara.display(grid)  # type: ignore[attr-defined]
            else:  # pragma: no cover - widget fallback
                renderer = getattr(grid, "_repr_html_", None)
                if callable(renderer):
                    solara.HTML(tag="div", unsafe_innerHTML=renderer(), classes=["pc-table-wrapper"])
                else:
                    raise RuntimeError("Cannot render ipyaggrid widget")
            return
        except Exception:  # noqa: BLE001
            prefer_aggrid = False

    if not rows:
        solara.Info("No issuances found for the selected window.")
        return

    table_html = _render_table(rows[:25])
    solara.HTML(tag="div", unsafe_innerHTML=table_html, classes=["pc-table-wrapper"])
    if len(rows) > 25:
        solara.Text(f"Showing first 25 of {len(rows)} rows. Export to view all.", classes=["caption"])
