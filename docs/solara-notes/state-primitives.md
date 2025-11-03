# State & Stores

See also: [Component Lifecycle](component-lifecycle.md) · [Rendering Pipeline](rendering-pipeline.md) · [Lists & Streaming](lists-and-streaming.md) · [Native Chat Review](native-chat-review.md)

## Reactive Foundations
- `solara.reactive` instantiates `Reactive` objects backed by `KernelStoreValue` (`solara/toestand.py`), giving each session its own scoped dictionary (`kernel_context.user_dicts`).
- Equality defaults to `solara.util.equals_extra`, a deep comparison tolerant of lists/dicts/ndarrays. Override equals when storing custom classes to avoid missed updates.
- `.value` is syntactic sugar for `.get()`/`.set()`; writes acquire a recursive lock, compare against previous value, and short-circuit if unchanged.

## Local State Hooks
- `solara.use_state` (re-exported from `reacton`) stores component-local state keyed by render position—ideal for transient UI flags.
- `solara.use_reactive` wraps `Reactive` creation in a hook, so the same object persists across renders without global scope; useful for message-level state like toolbar toggles.
- `solara.use_memo` caches expensive derivations; combine with dependencies to keep derived collections stable (e.g., message IDs for virtualization).

## Stores & Selectors
- `KernelStore` provides `.use(selector)` and `.use_state()` helpers; selectors allow derived reads without extra renders when unrelated fields change.
- `ValueBase.subscribe` attaches listeners per scope id and rebuilds the render context before invoking callbacks, ensuring updates run inside the right kernel/session.
- Prefer small immutable payloads in stores so `equals_extra` can efficiently diff; for mutability, provide a custom `merge` or wrap collections in dataclasses.

## Event Semantics
- Widget events trigger normal Python callbacks synchronous to the UI thread. When they mutate a `Reactive`, subscribers are notified immediately; Solara then schedules affected components for re-render.
- For async workflows, `solara.tasks.use_task` exposes `.pending`, `.value`, `.error`, and `.latest` so UIs can show optimistic or fallback content without blocking.
- Reactives can interoperate with hooks (`use_sync_external_store` adapters inside `ValueBase`) to keep external systems (websocket clients, stores) in sync with component updates.

## Practical Patterns
- Co-locate chat session state in a single dataclass reactive (messages, pending requests, attestation). Update via `merge_state` so partial updates remain atomic.
- Use `solara.use_memo` or `Reactive.setter(field)` to avoid recreating callbacks; stable references prevent child components from re-rendering unnecessarily.
- When bridging to file-backed storage, wrap IO in hooks (`use_task`, `use_thread`) so state writes remain responsive; update the `Reactive` once persistence completes to keep the UI consistent.
