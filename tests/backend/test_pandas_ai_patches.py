from __future__ import annotations

from app.backend.pandas_ai import patches


def test_register_and_apply(monkeypatch):
    applied = []

    @patches.register_patch
    def _patch() -> None:
        applied.append(True)

    patches.apply_all_patches()
    assert applied == [True]

    @patches.register_patch
    def _late_patch() -> None:
        applied.append("late")

    assert applied == [True, "late"]
