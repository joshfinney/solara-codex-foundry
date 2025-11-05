"""Helpers for loading global CSS assets once per session."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import solara


_BASE = Path(__file__).resolve().parent.parent
CSS_ASSETS = [
    _BASE / "ui" / "styles" / "sidebar.css",
    _BASE / "ui" / "styles" / "chat.css",
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
