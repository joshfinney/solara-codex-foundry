"""Sidebar wrapper for the conversational assistant."""

from __future__ import annotations

from typing import Callable

import solara

from ..core import styles
from ..core.state import AppController
from . import chat


@solara.component
def SidebarToggleButton(controller: AppController):
    state = controller.state.use(lambda s: s.ui.sidebar_open)

    def toggle():
        controller.toggle_sidebar()

    solara.Button("Close chat" if state else "Open chat", text=True, on_click=toggle)


@solara.component
def ChatSidebar(controller: AppController):
    styles.use_global_styles()
    app_state = controller.state.use()
    sidebar_open = app_state.ui.sidebar_open
    classes = ["pc-sidebar", "open" if sidebar_open else "closed"]
    with solara.Div(classes=classes):
        chat.ChatSidebar(controller.chat, app_state.ui.conversation_id)


@solara.component
def SidebarLayout(controller: AppController, body: Callable[[], None]):
    styles.use_global_styles()
    with solara.Div(classes=["pc-shell"]):
        body()
        ChatSidebar(controller)
