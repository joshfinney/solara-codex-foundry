"""Chat sidebar experience for the Primary Credit application."""

from __future__ import annotations

import threading
from typing import Callable

import solara

from solara_codex_foundry.chat import state as chat_state
from solara_codex_foundry.chat import view as chat_view

from ..services import telemetry


@solara.component
def StageTicker(active: bool):
    ticker = solara.use_memo(lambda: telemetry.SpanTicker(), [])
    label, set_label = solara.use_state(ticker.current_label())

    def effect():
        cancel = False
        if not active:
            ticker.reset()
            set_label(ticker.current_label())
            return

        def run():
            while not cancel:
                set_label(ticker.current_label())
                threading.Event().wait(ticker.interval_seconds)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        def cleanup():
            nonlocal cancel
            cancel = True

        return cleanup

    solara.use_effect(effect, [active])
    with solara.Row(classes=["chat-stage"], style={"alignItems": "center", "gap": "0.5rem"}):
        solara.v.ProgressCircular(indeterminate=True, size=16)
        solara.Text(label, classes=["caption", "text-medium-emphasis"])


@solara.component
def ConversationHeader(conversation_id: str, pending: bool):
    with solara.Row(justify="between", classes=["conversation-header"], style={"alignItems": "center"}):
        solara.Text(f"Conversation {conversation_id}", classes=["subtitle-2"])
        if pending:
            StageTicker(True)
        else:
            solara.Text("Assistant is idle", classes=["caption", "text-medium-emphasis"])


@solara.component
def EmptyState(prompt_categories: dict[str, list[str]], on_select: Callable[[str], None]):
    with solara.Column(classes=["chat-empty"], style={"gap": "0.75rem", "padding": "1rem"}):
        solara.Text("Ask the assistant anything about issuance trends.", classes=["body-1"])
        if prompt_categories:
            for title, prompts in prompt_categories.items():
                solara.Text(title, classes=["body-2", "text-medium-emphasis"])
                with solara.Row(style={"flexWrap": "wrap", "gap": "0.5rem"}):
                    for option in prompts:
                        solara.Button(option, outlined=True, on_click=lambda value=option: on_select(value))


@solara.component
def SidebarChatSurface(controller: chat_state.ChatController, conversation_id: str):
    chat_state_value = controller.state.use()
    composer_text, set_composer_text = solara.use_state("", key="pc-chat-composer")
    pending = bool(chat_state_value.pending_message_ids)

    def handle_send(*_ignore):
        if not composer_text.strip():
            return
        controller.send_user_message(composer_text)
        set_composer_text("")

    def handle_prompt_select(prompt: str):
        if not composer_text:
            set_composer_text(prompt)
        else:
            set_composer_text(f"{composer_text.rstrip()}\n{prompt}")

    with solara.Column(style={"height": "100%", "gap": "0.5rem"}):
        ConversationHeader(conversation_id, pending)
        if chat_state_value.messages:
            chat_view.VirtualMessageList(controller, on_prompt_select=handle_prompt_select)
        else:
            EmptyState(chat_state_value.prompt_categories, handle_prompt_select)
        with solara.Column(classes=["chat-composer"], style={"marginTop": "auto", "gap": "0.5rem"}):
            if pending:
                StageTicker(True)
            with solara.Row(style={"gap": "0.5rem"}):
                solara.InputTextArea(
                    "Write your prompt",
                    value=composer_text,
                    on_value=set_composer_text,
                    rows=3,
                    continuous_update=True,
                )
                solara.Button(
                    "Send",
                    color="primary",
                    disabled=pending or not composer_text.strip(),
                    on_click=handle_send,
                )


@solara.component
def ChatSidebar(controller: chat_state.ChatController, conversation_id: str):
    SidebarChatSurface(controller, conversation_id)
