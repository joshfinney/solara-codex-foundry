"""Allocations dashboard placeholder."""

from __future__ import annotations

import solara

from app.state import AppController


@solara.component
def View(controller: AppController) -> None:
    solara.Column(
        lambda: solara.Markdown(
            """
            ### Allocations insights

            Allocation analytics will live here shortly. The data services layer is being
            finalised so this surface focuses on the issuance grid for now.
            """
        ),
        classes=["pc-allocations"],
        style={
            "padding": "1rem 1.5rem",
            "background": "#ffffff",
            "borderRadius": "12px",
            "border": "1px solid rgba(15, 23, 42, 0.08)",
        },
    )
