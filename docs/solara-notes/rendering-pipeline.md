# Rendering Pipeline

See also: [Component Lifecycle](component-lifecycle.md) · [State & Stores](state-primitives.md) · [Lists & Streaming](lists-and-streaming.md) · [Native Chat Review](native-chat-review.md)

## From Component to DOM
- `@solara.component` functions compile to `reacton` elements, which map onto ipywidgets (often Vuetify widgets via `solara.v`). Widgets synchronize with the browser through the Jupyter protocol over websocket.
- When a component re-renders, Reacton diffs the virtual tree and updates only mutated widgets; Solara keeps widget identity stable using the element key (auto-generated from call-site + args).
- CSS and layout wrappers (e.g., `solara.Column`, `Row`, `Card`) create persistent containers. Removing a container forces widget teardown, producing reflow and flicker.

## Batch & Effect Phases
- Writes to `Reactive` values queue updates; Reacton batches them and executes the minimal set of renders synchronously.
- `use_effect` callbacks run after the DOM commits, ideal for imperative DOM tweaks or focusing inputs. Cleanup handlers run before re-running the effect or unmounting the component.
- `use_task` yields task objects that update in-place; their `.pending` flag allows rendering skeletons without swapping out the message containers.

## Avoiding Reflow & Flicker
- Maintain stable heights: wrap dynamic sections (code panel, feedback modal) in containers with fixed padding/border. Toggle visibility with CSS classes or `v_if` flags rather than destroying nodes.
- Use stable keys for list items; when mapping messages, key by message id or timestamp rather than index to prevent reorder-induced flicker.
- Defer expensive computation with `use_memo` so re-renders avoid recalculating block layouts; reuse memoized block renderers for identical message structures.
- Keep scrolling containers (chat transcript) mounted and reuse `slot` style updates; allow streaming text to update inner markdown widget content instead of rebuilding the entire message row.

## Observability & Debugging
- `solara.Style` injects scoped CSS tied to component UUIDs (see `solara/lab/components/chat.py`). Inline styles can adjust transitions without re-rendering siblings.
- Developer hooks like `solara.cache.memoize` and logging inside `Reactive.fire` help trace re-render cascades; enable `_DEBUG` in `toestand.py` for stack traces on state writes when diagnosing feedback loops.
