"""Minimal Solara stub for non-UI test execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Tuple


class _Reactive:
    def __init__(self, value: Any):
        self.value = value

    def set(self, value: Any) -> None:
        self.value = value

    def update(self, mutator: Callable[[Any], Any]) -> None:
        result = mutator(self.value)
        if isinstance(result, dict):
            for key, new_value in result.items():
                setattr(self.value, key, new_value)
        elif result is not None:
            self.value = result

    def use(self, selector: Optional[Callable[[Any], Any]] = None) -> Any:
        return selector(self.value) if selector else self.value


def reactive(value: Any) -> _Reactive:
    return _Reactive(value)


def component(fn: Callable) -> Callable:
    return fn


def use_state(initial: Any, *, key: str | None = None) -> Tuple[Any, Callable[[Any], None]]:
    def setter(value: Any) -> None:
        pass

    return initial, setter


def use_memo(factory: Callable[[], Any], deps: Iterable[Any]) -> Any:
    return factory()


def use_effect(effect: Callable[[], Optional[Callable[[], None]]], deps: Iterable[Any] | None = None) -> None:
    cleanup = effect()
    if callable(cleanup):
        cleanup()


def use_css(_: str) -> None:
    pass


def Style(*args, **kwargs):  # noqa: N802
    pass


def Markdown(*args, **kwargs):
    pass


def Text(*args, **kwargs):
    pass


def InputText(*args, **kwargs):
    pass


def InputTextArea(*args, **kwargs):
    pass


def Button(*args, **kwargs):
    pass


def Card(*args, **kwargs):
    pass


def Row(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        args[0]()


def Column(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        args[0]()


def Success(*args, **kwargs):
    pass


def ProgressLinear(*args, **kwargs):
    pass


def Info(*args, **kwargs):
    pass


def HTML(*args, **kwargs):
    pass


def SliderInt(*args, **kwargs):
    pass


def Switch(*args, **kwargs):
    pass


def Slider(*args, **kwargs):
    pass


class _VNamespace:
    def __getattr__(self, _name: str) -> Callable:
        def _noop(*args, **kwargs):
            pass

        return _noop


v = _VNamespace()
