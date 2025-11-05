"""Minimal Solara stub for non-UI test execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Tuple


@dataclass
class Route:
    path: str
    component: Callable[..., Any]
    name: Optional[str] = None


class _RouterState:
    def __init__(self):
        self.path = "/"

    def push(self, path: str) -> None:
        self.path = path


_router_state = _RouterState()


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


def Div(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        args[0]()


def Link(*, href: str, children: Optional[Callable[[], None]] = None, **_kwargs):
    if children:
        children()


def Image(*args, **kwargs):
    pass


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


def use_router():
    return _router_state


def Router(*, routes: Iterable[Route]):
    routes = list(routes)
    target = None
    for route in routes:
        if route.path == _router_state.path:
            target = route
            break
    if target is None and routes:
        target = routes[0]
    if target is None:
        return
    component = target.component
    if callable(component):
        component()


class _VNamespace:
    def __getattr__(self, _name: str) -> Callable:
        def _noop(*args, **kwargs):
            pass

        return _noop


v = _VNamespace()
