"""AI workspace entry point."""

from __future__ import annotations

import solara

from app.state import AppController


@solara.component
def View(controller: AppController) -> None:
    solara.Column(
        lambda: solara.Markdown(
            """
            ### Conversation workspace

            Use the AI assistant in the sliding panel to explore issuance analytics, craft
            prompt experiments, and review generated playbooks. The panel stays open by default,
            and you can use the header button to collapse it when you need a wider grid.
            """
        ),
        classes=["pc-ai-page"],
        style={
            "padding": "1rem 1.5rem",
            "background": "#ffffff",
            "borderRadius": "12px",
            "border": "1px solid rgba(15, 23, 42, 0.08)",
        },
    )
