# Lists & Streaming

See also: [Component Lifecycle](component-lifecycle.md) · [State & Stores](state-primitives.md) · [Rendering Pipeline](rendering-pipeline.md) · [Native Chat Review](native-chat-review.md)

## Stable Lists
- Derive message keys from deterministic identifiers (e.g., server-issued id, client nonce). Pass as `key` to child components so Reacton preserves widget identity.
- Native `ChatBox` achieves bottom anchoring via `flex-direction: column-reverse` but forces message reversal; prefer keeping natural order with `justify-content: flex-end` when virtualization or streaming require stable indices.
- Memoize renderers: `solara.use_memo` can cache block render functions keyed by `(block.type, block.metadata)` so re-renders reuse existing widgets.

## Virtualisation & Windowing
- For large histories, wrap the transcript in a virtualised scroller. Solara’s Vuetify stack supports manual windowing by slicing the message list based on scroll position; combine with a `Reactive` tracking viewport range.
- Ensure off-screen elements keep their keys reserved; maintain a stash of message metadata and render a limited subset while preserving container height via padding placeholders.

## Streaming & Placeholders
- For optimistic sends, append a provisional message with status metadata. When the backend responds, merge the payload into the same message id to avoid node replacement.
- Use `solara.tasks.use_task` or `use_thread` to process backend streams; update the message’s reactive field incrementally so the markdown widget mutates in place.
- Provide a typing indicator inside the list rather than a separate component; reusing the message container maintains scroll position.

## Long-List Performance
- Batch writes: coalesce rapid updates into a single `Reactive.update` call (leveraging `merge_state`) to minimize re-renders.
- Avoid synchronous heavy formatting in the render path; precompute summaries outside render and store them on the message model.
- Persist scroll state using `solara.use_ref` and `solara.use_effect` (attach to Vue `v-virtual-scroll` events) so resetting the list does not snap the viewport.
