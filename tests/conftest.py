"""Test configuration for ensuring the src package is importable."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_PATH):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
