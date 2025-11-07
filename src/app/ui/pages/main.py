"""Application routing and workspace composition."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict

import solara

from app.core import styles
from app.services import attestation, chat_backend
from app.services.logging import StructuredLogger
from app.services.storage import StorageClient
from app.state import AppController, ChatController
from app.ui.components import feedback, header, sidebar, workspace
from app.ui.components.auth import AuthorizationWrapper
from app.ui.pages import ai, allocations, new_issue

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ATTESTATION_FILE = PROJECT_ROOT / "storage" / "attestation_state.json"
PROMPT_SUGGESTIONS_FILE = PROJECT_ROOT / "storage" / "prompt_suggestions.json"

HOME_PATH = "/"
ROUTE_COMPONENTS: Dict[str, Callable[[AppController], None]] = {
    "/": new_issue.View,
    "/allocations": allocations.View,
    "/ai": ai.View,
}
ROUTE_TABS = {
    "/": "new_issues",
    "/allocations": "allocations",
    "/ai": "ai",
}

_controller_singleton: AppController | None = None


def load_prompt_suggestions() -> dict[str, list[str]]:
    if PROMPT_SUGGESTIONS_FILE.exists():
        try:
            return json.loads(PROMPT_SUGGESTIONS_FILE.read_text())
        except json.JSONDecodeError:  # pragma: no cover - defensive
            return {}
    return {}


def create_controller() -> AppController:
    logger = StructuredLogger()
    chat_controller = ChatController(
        backend_client=chat_backend.MockChatBackend(),
        attestation_store=attestation.FileAttestationStore(ATTESTATION_FILE),
        prompt_categories=load_prompt_suggestions(),
    )
    storage_client = StorageClient(logger)
    return AppController(
        chat_controller=chat_controller,
        logger=logger,
        storage_client=storage_client,
        execution_root=PROJECT_ROOT,
    )


def _get_controller() -> AppController:
    global _controller_singleton
    if _controller_singleton is None:
        _controller_singleton = create_controller()
    return _controller_singleton


@solara.component
def _WorkspaceShell(
    controller: AppController,
    *,
    current_path: str,
    render_content: Callable[[], None],
) -> None:
    session_state = controller.state.use(lambda s: s.session)
    ui_state = controller.state.use(lambda s: s.ui)
    expected_tab = ROUTE_TABS.get(current_path, "new_issues")

    def sync_tab():
        if ui_state.active_tab != expected_tab:
            controller.set_active_tab(expected_tab)

    solara.use_effect(sync_tab, [expected_tab, ui_state.active_tab])

    with solara.Column(
        classes=["pc-workspace"],
        style={
            "maxWidth": "1440px",
            "margin": "0 auto",
            "gap": "1rem",
            "padding": "1rem 0 1.5rem",
            "boxSizing": "border-box",
            "width": "100%",
            "flex": "1 1 auto",
        },
    ):
        with solara.Div(classes=["pc-workspace-section", "pc-workspace-section--flush"]):
            header.AppHeader(controller, current_path)
        with solara.Div(classes=["pc-workspace-section"]):
            workspace.WorkspaceToolbar(controller)
        with solara.Div(classes=["pc-workspace-section", "pc-workspace-content"]):
            if session_state.bootstrapping and not session_state.ready:
                solara.ProgressLinear(indeterminate=True)
                solara.Text(session_state.loading_label, classes=["caption"])
            else:
                render_content()
        with solara.Div(classes=["pc-workspace-section", "pc-workspace-section--flush"]):
            workspace.AppFooter(controller)


def _make_route(path: str, name: str) -> solara.Route:
    view = ROUTE_COMPONENTS.get(path, ROUTE_COMPONENTS[HOME_PATH])

    @solara.component
    def _route():
        controller = solara.use_memo(_get_controller, [])
        styles.use_global_styles()
        router = solara.use_router()
        current_path = router.path if router else path

        def body():
            view(controller)

        sidebar.SidebarLayout(
            controller,
            body=lambda: _WorkspaceShell(controller, current_path=current_path, render_content=body),
        )
        feedback.FeedbackModal(controller)

    return solara.Route(path=path, component=_route, name=name)


routes = [
    _make_route(HOME_PATH, "new-issue"),
    _make_route("/allocations", "allocations"),
    _make_route("/ai", "ai"),
]


@solara.component
def _AuthorizedRouter() -> None:
    solara.Router(routes=routes)


@solara.component
def Page():
    AuthorizationWrapper(
        component=_AuthorizedRouter,
        app_name="Primary Credit",
        display_name="Primary Credit Issuance Workspace",
    )
