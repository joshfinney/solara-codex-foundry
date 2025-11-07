"""Registry used to coordinate PandasAI monkey patches.

The live environment applies a number of patches to the upstream PandasAI
project to support richer response types.  The production system injects those
patches at import time which is difficult to replicate in tests.  The registry
below provides a predictable way for patches to be registered from any module
and ensures they are executed once in a thread-safe manner.
"""

from __future__ import annotations

import threading
from typing import Callable, List

PatchCallable = Callable[[], None]


class _PatchRegistry:
    """Stores patch callables and applies them once."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._patches: List[PatchCallable] = []
        self._applied = False

    def register(self, patch: PatchCallable) -> None:
        """Register a patch and execute it immediately when already patched."""

        if not callable(patch):  # pragma: no cover - defensive programming
            raise TypeError("patch must be callable")
        with self._lock:
            if self._applied:
                patch()
            else:
                self._patches.append(patch)

    def apply_all(self) -> None:
        with self._lock:
            if self._applied:
                return
            for patch in list(self._patches):
                patch()
            self._applied = True
            self._patches.clear()


_registry = _PatchRegistry()


def register_patch(patch: PatchCallable) -> PatchCallable:
    """Register a patch callback and return it for decorator usage."""

    _registry.register(patch)
    return patch


def apply_all_patches() -> None:
    """Apply registered patches if they have not already executed."""

    _registry.apply_all()
