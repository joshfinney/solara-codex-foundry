"""Top application bar showing branding and status badges."""

from __future__ import annotations

import solara

from app.state import AppController


@solara.component
def StatusChip(label: str, active: bool):
    color = "success" if active else "warning"
    solara.v.Chip(label=label, color=color, variant="outlined", classes=["status-chip"])


@solara.component
def AppHeader(controller: AppController):
    state = controller.state.use()
    with solara.v.AppBar(color="primary", dark=True, classes=["pc-app-bar"]):
        with solara.v.Btn(icon=True, on_click=controller.toggle_sidebar):
            solara.v.Icon(children=["mdi-menu"])
        solara.v.ToolbarTitle(children=["Primary Credit – Issuance Intelligence"])
        solara.v.Spacer()
        StatusChip("Authenticated" if state.gate.is_authenticated else "Guest", state.gate.is_authenticated)
        StatusChip("Attested", state.gate.has_accepted_terms)
        StatusChip("Ready" if state.session.ready else "Loading", state.session.ready)
