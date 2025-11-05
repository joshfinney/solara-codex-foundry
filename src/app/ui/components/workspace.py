"""Shared workspace controls and footer components."""

from __future__ import annotations

import datetime as _dt

import solara

from app.state import AppController


def _format_start_date(latest: _dt.date | None, lookback: int) -> tuple[str, str]:
    if latest is None or lookback <= 0:
        return ("Start date unavailable", "")
    start = latest - _dt.timedelta(days=lookback - 1)
    start_label = start.strftime("%b %d, %Y")
    delta_days = max(0, (_dt.date.today() - start).days)
    if delta_days == 0:
        ago = "Today"
    elif delta_days == 1:
        ago = "1 day ago"
    else:
        ago = f"{delta_days} days ago"
    return start_label, ago


@solara.component
def WorkspaceToolbar(controller: AppController) -> None:
    state = controller.state.use()
    dataset_state = state.dataset
    ui_state = state.ui
    latest = None
    if dataset_state.filtered and dataset_state.filtered.rows:
        last_row = dataset_state.filtered.rows[-1]
        latest_value = last_row.get("issue_date")
        if isinstance(latest_value, _dt.datetime):
            latest = latest_value.date()
        elif isinstance(latest_value, _dt.date):
            latest = latest_value
    if latest is None and dataset_state.raw and dataset_state.raw.latest_issue_date:
        latest = dataset_state.raw.latest_issue_date
    start_label, ago_label = _format_start_date(latest, dataset_state.lookback_days)

    with solara.Row(
        classes=["pc-toolbar"],
        style={"alignItems": "center", "justifyContent": "space-between"},
    ):
        with solara.Row(
            classes=["pc-toolbar-left"],
            style={"alignItems": "center", "gap": "0.75rem", "flex": "1 1 auto"},
        ):
            with solara.Column(style={"gap": "0.125rem"}):
                solara.Text(start_label, classes=["pc-toolbar-heading"])
                solara.Text(ago_label, classes=["pc-toolbar-subheading"])
            solara.SliderInt(
                label="Days",
                value=dataset_state.lookback_days,
                min=1,
                max=max(1, dataset_state.max_lookback_days),
                step=1,
                on_value=lambda value: controller.set_lookback_days(int(value)),
                classes=["pc-toolbar-slider"],
            )
        with solara.Row(
            classes=["pc-toolbar-right"],
            style={"alignItems": "center", "gap": "0.5rem"},
        ):
            if not ui_state.inline_feedback_open:
                solara.Button(
                    "Feedback",
                    text=True,
                    on_click=lambda: controller.set_inline_feedback_open(True),
                )
            else:
                solara.InputText(
                    "Share your thoughts",
                    value=ui_state.inline_feedback_text,
                    on_value=controller.update_inline_feedback_text,
                    continuous_update=True,
                    classes=["pc-feedback-input"],
                )
                solara.Button(
                    "Submit",
                    color="primary",
                    disabled=(
                        ui_state.inline_feedback_status == "submitting"
                        or not ui_state.inline_feedback_text.strip()
                    ),
                    on_click=controller.submit_inline_feedback,
                )
                solara.Button(
                    "Cancel",
                    text=True,
                    on_click=controller.cancel_inline_feedback,
                )
            if ui_state.inline_feedback_status == "submitted":
                solara.Text("Thanks for the feedback!", classes=["pc-feedback-success"])


@solara.component
def StatusPill(label: str, value: str) -> None:
    with solara.Row(classes=["pc-status-pill"], style={"alignItems": "center", "gap": "0.25rem"}):
        solara.Text(label, classes=["pc-status-label"])
        solara.Text(value, classes=["pc-status-value"])


@solara.component
def AppFooter(controller: AppController) -> None:
    state = controller.state.use()
    dataset_state = state.dataset
    session_state = state.session
    row_count = 0
    if dataset_state.filtered:
        row_count = dataset_state.filtered.row_count
    elif dataset_state.raw:
        row_count = dataset_state.raw.row_count

    pills = [
        ("Workspace", "Ready" if session_state.ready else session_state.loading_label),
        ("Celery", "Online" if session_state.celery_ready else "Offline"),
        ("Rows", f"{row_count:,}"),
        ("UID", state.gate.username or "unknown"),
    ]

    with solara.Row(
        classes=["pc-footer"],
        style={"justifyContent": "flex-start", "gap": "0.75rem", "alignItems": "center"},
    ):
        for label, value in pills:
            StatusPill(label, value)
