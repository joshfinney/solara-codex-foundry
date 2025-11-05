"""Primary Credit application workspace."""

from __future__ import annotations

import json
import os
from pathlib import Path

import solara

from app.components.chat import attestation, backend, state as chat_state

from ..components import feedback, grid, header, panels, sidebar
from ..core import gates, styles
from ..core.state import AppController
from ..services.logging import StructuredLogger
from ..services.storage import StorageClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATTESTATION_FILE = PROJECT_ROOT / "storage" / "attestation_state.json"
PROMPT_SUGGESTIONS_FILE = PROJECT_ROOT / "storage" / "prompt_suggestions.json"


def load_prompt_suggestions() -> dict[str, list[str]]:
    if PROMPT_SUGGESTIONS_FILE.exists():
        try:
            return json.loads(PROMPT_SUGGESTIONS_FILE.read_text())
        except json.JSONDecodeError:  # pragma: no cover - defensive
            return {}
    return {}


def create_controller() -> AppController:
    logger = StructuredLogger()
    chat_controller = chat_state.ChatController(
        backend_client=backend.MockChatBackend(),
        attestation_store=attestation.FileAttestationStore(ATTESTATION_FILE),
        prompt_categories=load_prompt_suggestions(),
    )
    storage_client = StorageClient(logger, bucket=os.getenv("PRIMARY_CREDIT_S3_BUCKET"))
    return AppController(chat_controller=chat_controller, logger=logger, storage_client=storage_client)


@solara.component
def Page():
    styles.use_global_styles()
    controller = solara.use_memo(create_controller, [])
    app_state = controller.state.use()

    if not app_state.gate.is_authenticated:
        gates.LoginGate(controller.authenticate)
        return
    if not app_state.gate.has_accepted_terms:
        gates.TermsGate(app_state.gate.attestation_message, controller.accept_terms)
        return

    sidebar.SidebarLayout(controller, body=lambda: _MainWorkspace(controller))
    feedback.FeedbackModal(controller)


@solara.component
def _MainWorkspace(controller: AppController):
    app_state = controller.state.use()
    with solara.Column(
        classes=["pc-workspace"],
        style={
            "maxWidth": "1400px",
            "margin": "0 auto",
            "padding": "1.5rem",
            "gap": "1rem",
            "boxSizing": "border-box",
        },
    ):
        header.AppHeader(controller)
        if app_state.session.bootstrapping and not app_state.session.ready:
            solara.ProgressLinear(indeterminate=True)
            solara.Text(app_state.session.loading_label, classes=["caption"])
            return

        with solara.Row(justify="start", style={"gap": "0.5rem"}):
            for tab, label in [("new_issues", "New Issues"), ("allocations", "Allocations")]:
                solara.Button(
                    label,
                    color="primary" if app_state.ui.active_tab == tab else None,
                    outlined=app_state.ui.active_tab != tab,
                    on_click=lambda value=tab: controller.set_active_tab(value),
                )

        if app_state.ui.active_tab == "allocations":
            with solara.Card(title="Allocations", style={"minHeight": "300px"}):
                solara.Markdown(
                    "This view is under construction. Allocation analytics will appear here soon.",
                )
            return

        with solara.Column(style={"gap": "1rem"}):
            with solara.Row(justify="between", style={"gap": "1rem", "alignItems": "stretch", "flexWrap": "wrap"}):
                with solara.Column(style={"flex": "2 1 360px", "gap": "1rem"}):
                    panels.LookbackPanel(controller)
                with solara.Column(style={"flex": "1 1 320px", "gap": "1rem"}):
                    panels.InlineFeedbackPanel(controller)
            grid.IssueGrid(controller)
