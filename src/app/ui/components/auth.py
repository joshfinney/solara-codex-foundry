"""Authorization wrapper applied to top-level routes."""

from __future__ import annotations

import os
from typing import Callable

import solara


def _environment_flag(name: str) -> bool:
    value = os.getenv(name, "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_app_name(app_name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in app_name).upper()


@solara.component
def DefaultUnauthorized(display_name: str):
    solara.Column(
        lambda: solara.Text(
            f"Access to {display_name} is not authorised for this account.",
        ),
        style={
            "maxWidth": "560px",
            "margin": "4rem auto",
            "padding": "1.5rem",
            "textAlign": "center",
        },
    )


@solara.component
def AuthorizationWrapper(
    component: Callable[[], None],
    *,
    app_name: str,
    display_name: str,
    unauthorized_component: Callable[[], None] | None = None,
):
    flag_name = f"{_normalize_app_name(app_name)}_AUTHORIZED"
    is_authorised = _environment_flag(flag_name)

    if is_authorised:
        component()
    else:
        if unauthorized_component is not None:
            unauthorized_component()
        else:
            DefaultUnauthorized(display_name)
