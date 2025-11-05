"""Sidebar wrapper for the conversational assistant."""

from __future__ import annotations

from typing import Callable

import solara

from app.core import styles
from app.state import AppController
from . import chat


@solara.component
def SidebarToggleButton(controller: AppController):
    state = controller.state.use(lambda s: s.ui.sidebar_open)

    def toggle():
        controller.toggle_sidebar()

    solara.Button("Close chat" if state else "Open chat", text=True, on_click=toggle)


@solara.component
def ChatSidebar(controller: AppController, *, sidebar_open: bool, conversation_id: str):
    styles.use_global_styles()
    classes = ["pc-sidebar", "open" if sidebar_open else "closed"]
    with solara.Div(classes=classes):
        chat.ChatSidebar(controller.chat, conversation_id)


@solara.component
def SidebarLayout(controller: AppController, body: Callable[[], None]):
    styles.use_global_styles()
    # Only subscribe to the sidebar specific flags so unrelated UI updates
    # (e.g. inline feedback typing) do not force the workspace body to re-render.
    sidebar_open = controller.state.use(lambda s: s.ui.sidebar_open)
    conversation_id = controller.state.use(lambda s: s.ui.conversation_id)
    shell_classes = ["pc-shell"]
    if sidebar_open:
        shell_classes.append("sidebar-open")
    with solara.Div(classes=shell_classes):
        with solara.Div(classes=["pc-main"]):
            body()
        ChatSidebar(controller, sidebar_open=sidebar_open, conversation_id=conversation_id)
