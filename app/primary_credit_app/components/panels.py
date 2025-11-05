"""Workspace panels for filters, stats, and inline feedback."""

from __future__ import annotations

import solara

from ..core.state import AppController


@solara.component
def LookbackPanel(controller: AppController):
    dataset_state = controller.state.use(lambda s: s.dataset)
    filtered = dataset_state.filtered
    row_count = filtered.row_count if filtered else (dataset_state.raw.row_count if dataset_state.raw else 0)
    caption = f"Showing last {dataset_state.lookback_days} days" if dataset_state.lookback_days > 1 else "Showing last day"
    with solara.Card(title="Lookback window", style={"width": "100%"}):
        solara.Text(caption, classes=["caption", "text-medium-emphasis"])
        solara.v.Slider(
            min=1,
            max=max(1, dataset_state.max_lookback_days),
            step=1,
            v_model=dataset_state.lookback_days,
            on_v_model=lambda value: controller.set_lookback_days(int(value)),
            label="Day range",
        )
        solara.Text(f"{row_count} issues displayed", classes=["body-2"])


@solara.component
def InlineFeedbackPanel(controller: AppController):
    ui_state = controller.state.use(lambda s: s.ui)
    status = ui_state.inline_feedback_status
    with solara.Card(title="Quick feedback", style={"width": "100%"}):
        solara.Text(
            "Let us know how the issuance view is working for you.",
            classes=["body-2", "text-medium-emphasis"],
        )
        solara.InputTextArea(
            "Comments",
            value=ui_state.inline_feedback_text,
            on_value=controller.update_inline_feedback_text,
            continuous_update=True,
            rows=3,
        )
        with solara.Row(justify="end", style={"marginTop": "0.5rem"}):
            solara.Button(
                "Submit",
                color="primary",
                disabled=status == "submitting" or not ui_state.inline_feedback_text.strip(),
                on_click=controller.submit_inline_feedback,
            )
        if status == "submitted":
            solara.Success("Thanks for your feedback!")
        elif status == "submitting":
            solara.ProgressLinear(indeterminate=True)
