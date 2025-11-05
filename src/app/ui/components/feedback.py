"""Feedback modal used to collect structured assistant feedback."""

from __future__ import annotations

from dataclasses import dataclass

import solara

from app.state import AppController


@dataclass(frozen=True)
class FeedbackDefaults:
    score: int = 7
    minutes_saved: int = 0
    comments: str = ""
    chained: bool = False
    first_iteration_reference: str = ""


DEFAULTS = FeedbackDefaults()
G_FEEDBACK_ACTIVE_INDEX: solara.Reactive[int | None] = solara.reactive(None)


def open_feedback_for_message(index: int) -> None:
    G_FEEDBACK_ACTIVE_INDEX.value = index


def reset_feedback() -> None:
    G_FEEDBACK_ACTIVE_INDEX.value = None


@solara.component
def FeedbackModal(controller: AppController):
    active = G_FEEDBACK_ACTIVE_INDEX.use()
    if active is None:
        return

    score, set_score = solara.use_state(DEFAULTS.score, key="feedback-score")
    minutes, set_minutes = solara.use_state(DEFAULTS.minutes_saved, key="feedback-minutes")
    comments, set_comments = solara.use_state(DEFAULTS.comments, key="feedback-comments")
    chained, set_chained = solara.use_state(DEFAULTS.chained, key="feedback-chained")
    reference, set_reference = solara.use_state(DEFAULTS.first_iteration_reference, key="feedback-reference")

    def handle_submit():
        controller.logger.info(
            "feedback.modal.submitted",
            index=active,
            score=score,
            minutes_saved=minutes,
            comments=comments,
            chained=chained,
            first_iteration_reference=reference,
        )
        set_score(DEFAULTS.score)
        set_minutes(DEFAULTS.minutes_saved)
        set_comments(DEFAULTS.comments)
        set_chained(DEFAULTS.chained)
        set_reference(DEFAULTS.first_iteration_reference)
        reset_feedback()

    def handle_close():
        reset_feedback()

    with solara.v.Dialog(v_model=True, persistent=True, max_width=520, on_v_model=lambda _: handle_close()):
        with solara.Card(title="Assistant feedback", style={"padding": "1rem"}):
            solara.Text("Help us improve the assistant responses.", classes=["body-2"])
            solara.SliderInt("Score (0-10)", value=score, min=0, max=10, on_value=set_score)
            solara.SliderInt("Minutes saved", value=minutes, min=0, max=60, on_value=set_minutes)
            solara.Switch(label="Prompt was part of a chain", value=chained, on_value=set_chained)
            solara.InputTextArea(
                "Comments",
                value=comments,
                on_value=set_comments,
                continuous_update=True,
                rows=3,
            )
            solara.InputText(
                label="Reference for first iteration",
                value=reference,
                on_value=set_reference,
                continuous_update=True,
            )
            with solara.Row(justify="end", style={"marginTop": "1rem", "gap": "0.5rem"}):
                solara.Button("Cancel", text=True, on_click=handle_close)
                solara.Button("Submit", color="primary", on_click=handle_submit)
