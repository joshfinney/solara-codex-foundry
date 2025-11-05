"""Issuance grid rendered with ipyaggrid and rich defaults."""

from __future__ import annotations

from typing import Iterable

import solara
from ipyaggrid import Grid

from app.core.pandas_compat import pd

from app.state import AppController


def _formatter_for_series(series: pd.Series) -> dict[str, object]:
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return {"valueFormatter": {"function": "value ? new Date(value).toLocaleDateString() : ''"}}
    if pd.api.types.is_numeric_dtype(series.dtype):
        return {
            "type": "numericColumn",
            "valueFormatter": {"function": "value != null ? value.toLocaleString() : ''"},
        }
    return {}


def _build_column_defs(frame: pd.DataFrame) -> list[dict[str, object]]:
    column_defs: list[dict[str, object]] = []
    for column in frame.columns:
        base_def: dict[str, object] = {
            "headerName": column.replace("_", " ").title(),
            "field": column,
            "sortable": True,
            "filter": True,
            "resizable": True,
        }
        base_def.update(_formatter_for_series(frame[column]))
        column_defs.append(base_def)
    return column_defs


@solara.component
def IssueGrid(controller: AppController):
    dataset_state = controller.state.use(lambda s: s.dataset)
    filtered = dataset_state.filtered
    rows = filtered.rows if filtered else (dataset_state.raw.rows if dataset_state.raw else [])
    frame = filtered.frame if filtered and filtered.frame is not None else (
        dataset_state.raw.frame if dataset_state.raw else None
    )

    if frame is None or frame.empty:
        if not rows:
            solara.Info("No issuances found for the selected window.")
        else:
            solara.Text("Dataset preview unavailable.")
        return

    column_defs = _build_column_defs(frame)
    grid_options = {
        "columnDefs": column_defs,
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
            "minWidth": 120,
        },
        "animateRows": True,
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                },
                {
                    "id": "filters",
                    "labelDefault": "Filters",
                    "iconKey": "filter",
                    "toolPanel": "agFiltersToolPanel",
                },
            ]
        },
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agTotalRowCountComponent", "align": "left"},
                {"statusPanel": "agFilteredRowCountComponent"},
                {"statusPanel": "agAggregationComponent"},
            ]
        },
        "rowSelection": "multiple",
        "suppressCellFocus": True,
    }

    # Keep the grid widget stable across UI re-renders (e.g. sidebar toggles)
    # so ipyaggrid does not briefly unmount and remount, which causes a flash.
    frame_identity = id(frame)

    grid = solara.use_memo(
        lambda: Grid(
            grid_data=frame,
            grid_options=grid_options,
            columns_fit="size_to_fit",
            quick_filter=True,
            exportMode="auto",
            theme="ag-theme-alpine",
        ),
        dependencies=[frame_identity],
    )

    def render_widget():
        if hasattr(solara, "display"):
            solara.display(grid)  # type: ignore[attr-defined]
        else:  # pragma: no cover - widget fallback for tests
            renderer = getattr(grid, "_repr_html_", None)
            if callable(renderer):
                solara.HTML(tag="div", unsafe_innerHTML=renderer(), classes=["pc-grid-container"])
            else:
                solara.Text("Unable to render grid widget.")

    solara.Div(render_widget, classes=["pc-grid-container"])
