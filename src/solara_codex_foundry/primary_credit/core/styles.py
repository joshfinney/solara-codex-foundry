"""Helpers for loading global CSS assets once per session."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import solara


CSS_ASSETS = [
    Path(__file__).resolve().parent.parent / "styles" / "sidebar.css",
    Path(__file__).resolve().parent.parent / "styles" / "chat.css",
]


@solara.memoize
def use_global_styles(extra_assets: Iterable[Path] | None = None) -> None:
    """Inject CSS assets into the current Solara document."""

    assets = list(CSS_ASSETS)
    if extra_assets:
        assets.extend(Path(asset) for asset in extra_assets)
    for asset in assets:
        if asset.exists():
            solara.use_css(asset.read_text())
