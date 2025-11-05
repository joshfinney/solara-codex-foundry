# UI components composing the chat experience.

from __future__ import annotations

import html
from typing import Callable, Dict, Iterable, List, Optional

import solara
from solara.lab.components.chat import ChatMessage as LabChatMessage

from . import models, state

MAX_VISIBLE_MESSAGES = 30
OVERSCAN = 5


def _render_table(rows: Iterable[dict]) -> str:
    headers: List[str] = []
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
    return f"<table class='chat-table'><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"


@solara.component
def MessageBlockView(block: models.MessageBlock):
    """Render a single message block without disrupting layout."""

    for part in block.parts:
        if part.kind == "text":
            solara.Markdown(part.text or "")
        elif part.kind == "integer":
            solara.Text(f"{part.integer_value}")
        elif part.kind == "image":
            if part.image_path:
                solara.Image(part.image_path, width="100%")
        elif part.kind == "table":
            if part.table_rows:
                solara.HTML(tag="div", unsafe_innerHTML=_render_table(part.table_rows), classes=["chat-table-wrapper"])
        elif part.kind == "kv":
            if part.kv_pairs:
                rows = "".join(
                    f"<div class='kv-row'><span class='kv-key'>{html.escape(str(key))}</span><span class='kv-value'>{html.escape(str(value))}</span></div>"
                    for key, value in part.kv_pairs
                )
                solara.HTML(tag="div", unsafe_innerHTML=f"<div class='kv-wrapper'>{rows}</div>", classes=["chat-kv-wrapper"])
        else:  # pragma: no cover - defensive
            solara.Text("Unsupported block fragment.")


@solara.component
def CodePanel(msg: models.Message):
    expanded = not msg.toolbar_collapsed
    if not expanded or not msg.metadata.python_code:
        return

    with solara.Div(classes=["code-panel"], style={"width": "100%"}):
        solara.Markdown(f"```python\n{msg.metadata.python_code}\n```")


@solara.component
def FeedbackPanel(
    msg: models.Message,
    controller: state.ChatController,
    draft: models.FeedbackDraft,
    record: models.FeedbackRecord | None,
):
    if record is not None:
        with solara.Div(classes=["feedback-panel"], style={"width": "100%"}):
            solara.Success(f"Thanks! Minutes saved: {record.minutes_saved}, score: {record.score}/10")
            if record.comments:
                solara.Markdown(f"> {record.comments}")
        return

    with solara.Div(classes=["feedback-panel"], style={"width": "100%"}):
        def update_minutes(value):
            controller.update_feedback_draft(
                msg.id,
                lambda current: models.FeedbackDraft(
                    minutes_saved=int(value),
                    score=current.score,
                    comments=current.comments,
                ),
            )

        def update_score(value):
            controller.update_feedback_draft(
                msg.id,
                lambda current: models.FeedbackDraft(
                    minutes_saved=current.minutes_saved,
                    score=int(value),
                    comments=current.comments,
                ),
            )

        def update_comments(value):
            controller.update_feedback_draft(
                msg.id,
                lambda current: models.FeedbackDraft(
                    minutes_saved=current.minutes_saved,
                    score=current.score,
                    comments=value,
                ),
            )

        def handle_submit():
            controller.submit_feedback(msg.id)

        solara.Text(f"Minutes saved: {draft.minutes_saved}")
        solara.v.Slider(min=0, max=60, step=5, v_model=draft.minutes_saved, on_v_model=update_minutes, label="Minutes saved")
        solara.Text(f"Score: {draft.score}/10")
        solara.v.Slider(min=1, max=10, step=1, v_model=draft.score, on_v_model=update_score, label="Score")
        solara.InputTextArea("Comments", value=draft.comments, on_value=update_comments, continuous_update=True)
        with solara.Row(justify="end", style={"marginTop": "0.5rem"}):
            solara.Button("Submit", color="primary", on_click=handle_submit)


@solara.component
def MessageAssistantExtras(msg: models.Message, controller: state.ChatController):
    if msg.role != "assistant":
        return

    chat_state = controller.state.use()
    feedback_open = chat_state.active_feedback_message_id == msg.id
    submitted_record = chat_state.feedback_submissions.get(msg.id)
    draft = chat_state.feedback_drafts.get(msg.id, models.FeedbackDraft())
    code_open = not msg.toolbar_collapsed and bool(msg.metadata.python_code)

    def toggle_code():
        controller.toggle_code_panel(msg.id)

    def toggle_feedback():
        controller.toggle_feedback_panel(msg.id)

    with solara.Row(justify="start", classes=["message-toolbar"], style={"gap": "0.5rem"}):
        solara.Button("Hide code" if code_open else "View code", outlined=True, on_click=toggle_code)
        solara.Button(
            "Feedback submitted" if submitted_record else ("Hide feedback" if feedback_open else "Give feedback"),
            outlined=not submitted_record,
            color="success" if submitted_record else None,
            disabled=bool(submitted_record),
            on_click=None if submitted_record else toggle_feedback,
        )

    if code_open:
        CodePanel(msg)

    if feedback_open:
        FeedbackPanel(
            msg,
            controller,
            draft=draft,
            record=submitted_record,
        )


@solara.component
def MessageView(msg: models.Message, controller: state.ChatController):
    """Render a chat message with toolbar and optional code panel."""

    role_label = "You" if msg.role == "user" else "Assistant"
    bubble_color = "rgba(33, 150, 243, 0.18)" if msg.role == "user" else "rgba(0,0,0,0)"

    with solara.Column(classes=["chat-message-wrapper"], style={"width": "100%", "gap": "0.25rem"}):
        with LabChatMessage(
            user=msg.role == "user",
            name=role_label,
            color=bubble_color,
            avatar=False,
            notch=True,
            classes=["chat-message"],
            style={"width": "100%"},
        ):
            for block in msg.blocks:
                MessageBlockView(block)
        MessageAssistantExtras(msg, controller)


@solara.component
def PromptSuggestions(categories: Dict[str, List[str]], on_select: Callable[[str], None]):
    if not categories:
        return

    solara.Text("Prompt suggestions", classes=["subtitle-1", "prompt-heading"])
    for title, prompts in categories.items():
        with solara.Column(classes=["prompt-category"], style={"gap": "0.5rem"}):
            solara.Text(title, classes=["body-2", "text-medium-emphasis"])
            with solara.Row(style={"flexWrap": "wrap", "gap": "0.5rem"}):
                for prompt in prompts:
                    solara.Button(
                        prompt,
                        outlined=True,
                        on_click=lambda p=prompt: on_select(p),
                        style={
                            "whiteSpace": "normal",
                            "textAlign": "left",
                            "maxWidth": "280px",
                        },
                    )


@solara.component
def VirtualMessageList(
    controller: state.ChatController,
    on_prompt_select: Optional[Callable[[str], None]] = None,
    max_visible: int = MAX_VISIBLE_MESSAGES,
):
    st = controller.state.use()
    messages = st.messages
    start_index, set_start_index = solara.use_state(0, key="virtual-start")
    auto_follow, set_auto_follow = solara.use_state(True, key="auto-follow")

    def adjust_window():
        if auto_follow:
            new_start = max(0, len(messages) - max_visible)
            set_start_index(new_start)

    solara.use_effect(adjust_window, [len(messages), auto_follow])

    start_index = max(0, min(start_index, max(0, len(messages) - 1)))
    end_index = min(len(messages), start_index + max_visible + OVERSCAN)
    visible = messages[start_index:end_index]

    with solara.Div(
        classes=["virtual-list"],
        style={
            "height": "100%",
            "minHeight": 0,
            "flex": "1 1 auto",
            "overflow": "auto",
            "padding": "0.5rem",
            "paddingBottom": "1.5rem",
            "display": "flex",
            "flex-direction": "column",
            "justify-content": "flex-end",
        },
    ):
        if start_index > 0:
            def load_older():
                set_auto_follow(False)
                set_start_index(max(0, start_index - max_visible))

            def jump_latest():
                set_auto_follow(True)
                set_start_index(max(0, len(messages) - max_visible))

            with solara.Row(justify="between", style={"marginBottom": "0.5rem"}):
                solara.Button("Load earlier messages", outlined=True, on_click=load_older)
                solara.Button("Jump to latest", text=True, on_click=jump_latest)
        if not messages and on_prompt_select:
            PromptSuggestions(st.prompt_categories, on_prompt_select)

        for msg in visible:
            alignment = "flex-end" if msg.role == "user" else "flex-start"
            with solara.Div(
                classes=["virtual-item"],
                style={
                    "marginBottom": "0.75rem",
                    "display": "flex",
                    "justifyContent": alignment,
                    "width": "100%",
                },
            ):
                MessageView(msg, controller)


@solara.component
def ChatInput(controller: state.ChatController, message_text: str, set_message_text: Callable[[str], None]):
    is_pending = controller.state.use(lambda s: bool(s.pending_message_ids))

    def handle_send(*_ignore):
        if not message_text.strip():
            return
        controller.send_user_message(message_text)
        set_message_text("")

    with solara.Row(
        classes=["chat-input"],
        style={
            "alignItems": "center",
            "padding": "0.75rem",
            "gap": "0.5rem",
            "background": "white",
            "marginTop": "auto",
        },
    ):
        with solara.Column(style={"flex": "1 1 auto"}):
            solara.InputTextArea("Message", value=message_text, on_value=set_message_text, rows=3, continuous_update=True)
        solara.Button("Send", color="primary", disabled=is_pending or not message_text.strip(), on_click=handle_send)


@solara.component
def AttestationGate(controller: state.ChatController):
    attestation_state = controller.state.use(lambda s: s.attestation)
    if not attestation_state.required:
        return

    def accept():
        controller.record_attestation(True)

    with solara.Card(title="Before you continue", style={"maxWidth": "420px", "margin": "2rem auto"}):
        solara.Markdown("Please confirm that you will review AI responses before use.")
        with solara.Row(justify="end", style={"marginTop": "1rem"}):
            solara.Button("I understand", color="primary", on_click=accept)


@solara.component
def ChatSurface(controller: state.ChatController):
    """High-level shell that decides whether to show attestation or chat UI."""

    attestation_state = controller.state.use(lambda s: s.attestation)
    composer_text, set_composer_text = solara.use_state("")

    def apply_prompt(prompt: str):
        existing = composer_text.strip()
        if not existing:
            set_composer_text(prompt)
        else:
            set_composer_text(f"{composer_text.rstrip()}\n{prompt}")

    with solara.Div(
        classes=["chat-surface"],
        style={
            "height": "100vh",
            "minHeight": "0",
            "display": "flex",
            "flexDirection": "column",
            "padding": "1rem",
            "boxSizing": "border-box",
            "gap": "1rem",
        },
    ):
        solara.Style(
            """
            .chat-surface {
                background: var(--chat-surface-bg, #f7f9fc);
            }
            .virtual-list {
                background: white;
                border-radius: 8px;
                box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04);
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
            }
            .chat-message {
                width: 100%;
            }
            .chat-message-wrapper {
                width: 100%;
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            .message-toolbar {
                margin-top: 0.5rem;
            }
            .chat-input {
                border-top: 1px solid rgba(0,0,0,0.08);
            }
            .virtual-item {
                width: 100%;
            }
            .code-panel {
                background: rgba(0,0,0,0.04);
                border-radius: 6px;
                padding: 0.75rem;
            }
            .feedback-panel {
                background: rgba(0,0,0,0.02);
                border-radius: 6px;
                padding: 0.75rem;
                margin-top: 0.5rem;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            .chat-table {
                width: 100%;
                border-collapse: collapse;
            }
            .chat-table th,
            .chat-table td {
                border: 1px solid rgba(0,0,0,0.08);
                padding: 4px 6px;
                text-align: left;
            }
            .chat-kv-wrapper {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
                margin: 0.25rem 0;
            }
            .kv-row {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
            }
            .kv-key {
                font-weight: 600;
                color: rgba(0,0,0,0.7);
            }
            .kv-value {
                font-family: var(--chat-mono, 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace);
            }
            .prompt-heading {
                margin-bottom: 0.5rem;
                font-weight: 600;
            }
            .prompt-category {
                background: rgba(0,0,0,0.02);
                border-radius: 6px;
                padding: 0.5rem;
            }
            """
        )
        if attestation_state.required and not attestation_state.accepted:
            AttestationGate(controller)
        else:
            with solara.Card(
                style={
                    "flex": "1 1 auto",
                    "display": "flex",
                    "flexDirection": "column",
                    "overflow": "hidden",
                }
            ):
                solara.Text("Solara Chat Prototype", classes=["headline5"], style={"padding": "0.75rem", "paddingBottom": "0"})
                VirtualMessageList(controller, on_prompt_select=apply_prompt)
                ChatInput(controller, composer_text, set_composer_text)
