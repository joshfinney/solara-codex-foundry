"""New Issue workspace view."""

from __future__ import annotations

import solara

from app.state import AppController
from app.ui.components import grid


@solara.component
def View(controller: AppController) -> None:
    grid.IssueGrid(controller)
