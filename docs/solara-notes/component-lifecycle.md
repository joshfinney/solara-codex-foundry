# Component Lifecycle

See also: [State & Stores](state-primitives.md) · [Rendering Pipeline](rendering-pipeline.md) · [Lists & Streaming](lists-and-streaming.md) · [Native Chat Review](native-chat-review.md)

## Instantiation & Validation
- Function components are decorated with `@solara.component`, which wraps the function via `solara/core.py` and forwards to `reacton.component` after hook validation (`solara/validate_hooks.py` guards against misordered hooks).
- Invocation returns a lightweight element immediately; actual execution is deferred until the virtual tree renders, matching the lazy semantics described in `solara/website/.../10-components.md`.
- Component functions may return a single element or rely on implicit container creation; multiple child elements are wrapped in a `Column`.

## Render Cycle
- Each render runs the component body top-to-bottom. Hooks rely on call-order consistency; Solara mirrors React’s semantics (`reacton.use_state`, `use_memo`, etc.).
- Dependencies control re-execution: `use_memo` caches values, `use_effect` queues post-render callbacks, and `use_task` (from `solara/tasks.py`) schedules work after the commit phase.
- `solara.display` allows imperative child insertion while preserving the parent container, preventing layout thrash when streaming widgets into an existing box.

## Context & Lifetimes
- Stateful primitives (`solara.reactive`, `solara.use_reactive`) maintain scope isolation per virtual kernel via `KernelStore` (`solara/toestand.py`). Each browser session receives its own storage key, so tearing down a session automatically releases the state.
- Components mount within a kernel context managed by `solara.server.kernel_context`; context changes propagate through `ValueBase.fire`, ensuring events re-render the correct subtree only.
- Cleanup is managed by returning callables from `use_effect` hooks or using `solara.lifecycle.on_kernel_start` for global listeners; cleanups run when dependencies change or the component unmounts.

## Events & Propagation
- UI widgets expose callbacks (`on_click`, `on_value`) that run inside the component’s context, enabling synchronous state writes without race conditions.
- Reactive updates (`Reactive.set`) acquire a recursive lock, compare values with `equals_extra`, mutate the scoped store, then call `fire` to notify subscribers; listeners execute inside the preserved render/kernel contexts.
- Because listeners are scoped, events only travel to components that subscribed to the reactive during render, preventing cross-session leakage.

## Practical Guardrails
- Maintain deterministic hook ordering: wrap conditional UI blocks in child components instead of gating hook calls.
- Keep parent containers mounted across renders (e.g., `solara.Column`, `solara.Card`) so expanding content (code panels, modals) does not rebuild the list root—critical for flicker-free chat histories.
- When integrating long-running tasks, prefer `use_task` with dependency arrays to avoid blocking the main render path; leverage the `.pending` and `.latest` flags to display non-blocking placeholders.
