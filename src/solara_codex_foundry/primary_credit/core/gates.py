"""Authentication and attestation gates for the primary credit app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import solara


@dataclass
class GateState:
    """Minimal state required for the login/attestation flow."""

    is_authenticated: bool = False
    has_accepted_terms: bool = False
    username: Optional[str] = None
    attestation_message: str = (
        "I confirm that I will validate AI output before using it for credit decisions."
    )


@solara.component
def LoginGate(on_submit):  # type: ignore[override]
    """Render the login gate and call ``on_submit`` with the username."""

    username, set_username = solara.use_state("", key="login-username")
    password, set_password = solara.use_state("", key="login-password")
    is_submitting, set_submitting = solara.use_state(False, key="login-submitting")

    def handle_submit():
        if not username.strip() or not password.strip():
            return
        set_submitting(True)
        on_submit(username.strip())
        set_submitting(False)

    with solara.Card(title="Sign in", style={"maxWidth": "420px", "margin": "4rem auto"}):
        solara.InputText(label="Username", value=username, on_value=set_username, continuous_update=True)
        solara.InputText(
            label="Password",
            value=password,
            on_value=set_password,
            password=True,
            continuous_update=True,
        )
        with solara.Row(justify="end", style={"marginTop": "1rem"}):
            solara.Button(
                "Continue",
                color="primary",
                disabled=not username.strip() or not password.strip() or is_submitting,
                on_click=handle_submit,
            )


@solara.component
def TermsGate(attestation_message: str, on_accept):  # type: ignore[override]
    """Render the attestation acknowledgement."""

    with solara.Card(title="Primary Credit – Terms", style={"maxWidth": "520px", "margin": "3rem auto"}):
        solara.Markdown(
            "\n".join(
                [
                    "Before accessing the issuance workspace please confirm the following:",
                    f"- {attestation_message}",
                    "- You will only share the assistant output with authorized recipients.",
                    "- You understand that allocations remain subject to compliance review.",
                ]
            )
        )
        with solara.Row(justify="end", style={"marginTop": "1rem"}):
            solara.Button("I agree", color="primary", on_click=on_accept)
