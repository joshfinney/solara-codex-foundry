"""Header layout built with Solara rows and custom CSS."""

from __future__ import annotations

from typing import Iterable

import solara
from solara.labs import headers as header_utils

from app.state import AppController

NAV_LINKS: Iterable[tuple[str, str]] = (
    ("/", "New Issue"),
    ("/allocations", "Allocations"),
)


@solara.component
def HeaderNav(current_path: str) -> None:
    for path, label in NAV_LINKS:
        is_active = current_path == path

        def render_text(text: str = label, active: bool = is_active) -> None:
            classes = ["pc-header-tab"]
            if active:
                classes.append("active")
            solara.Text(text, classes=classes)

        solara.Link(href=path, children=render_text)


@solara.component
def AppHeader(controller: AppController, current_path: str) -> None:
    app_state = controller.state.use()
    public_config = app_state.session.public_config
    version = public_config.get("app_version", "dev")
    environment = public_config.get("environment", "local").upper()
    user_profile = header_utils.use_user()
    controller.set_user_profile(
        uid=user_profile.uid,
        first_name=user_profile.first_name,
        display_name=user_profile.display_name,
    )

    with solara.Row(
        classes=["pc-header"],
        style={"justifyContent": "space-between", "alignItems": "center"},
    ):
        with solara.Row(
            classes=["pc-header-left"],
            style={"alignItems": "center", "gap": "0.75rem"},
        ):
            solara.Div(lambda: solara.Text("PC"), classes=["pc-logo"])
            with solara.Column(style={"gap": "0.125rem"}):
                solara.Text("Primary Credit Issuance", classes=["pc-title"])
                with solara.Row(
                    style={"gap": "0.5rem", "alignItems": "center"}
                ):
                    solara.Text(f"v{version}", classes=["pc-meta"])
                    solara.Text("Beta", classes=["pc-badge"])
                    solara.Text(environment, classes=["pc-meta", "pc-env"])
        with solara.Row(
            classes=["pc-header-right"],
            style={"alignItems": "center", "gap": "1rem"},
        ):
            HeaderNav(current_path)
            solara.Button(
                f"AI • {user_profile.first_name}",
                color="primary",
                on_click=controller.toggle_sidebar,
                classes=["pc-ai-button"],
            )
