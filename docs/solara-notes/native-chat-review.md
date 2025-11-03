# Native Chat Review

See also: [Component Lifecycle](component-lifecycle.md) · [State & Stores](state-primitives.md) · [Lists & Streaming](lists-and-streaming.md)

## Solara Lab Components
- `ChatBox` (`solara.lab.components.chat.ChatBox`) wraps a `solara.Column` with `flex-direction: column-reverse`, `overflow-y: auto`, and reverses its children. This keeps the newest message pinned to the bottom without needing scroll logic but breaks natural order iteration and complicates virtualization.
- `ChatInput` manages its own `use_state` to buffer text and emits via `send_callback`. The internal `solara.v.TextField` is single-line, optimistic send resets immediately, and Enter key triggers via `use_change`.
- `ChatMessage` renders left/right bubbles with optional avatars, using scoped CSS tied to a per-instance UUID. It is otherwise stateless and expects the parent to control ordering and metadata labels.

## Pros & Cons
- **Pros:** Minimal surface area, good default styling (bubbles, notches, spacing); `ChatBox` ensures layout consistency even with short histories; components are stateless so they compose easily.
- **Cons:** `ChatBox`'s column-reverse strategy requires reversing message arrays on every render and breaks stable keys for dynamic lists—problematic for streaming updates and virtualization. `ChatInput` couples local state and reset behaviour, making external optimistic updates harder. None of the lab components handle backend coordination, feedback, or attestation; state management is left entirely to callers, which can lead to inconsistent UX.

## Implications for Our Library
- We reuse `ChatMessage` directly to match Solara’s native look, but we avoid `ChatBox`'s reversal so we can maintain stable keys and support windowed rendering.
- Our `VirtualMessageList` keeps a `flex` column but sets `justify-content: flex-end` to retain bottom anchoring without reversing data; this allows optimistic updates and streaming to patch in-place.
- The input component remains multi-line and controller-driven, so higher-level state (optimistic sends, disabled state) stays centralized in `ChatController`.
- Styling tokens are kept close to native defaults (colors, notch, padding) so migration preserves Solara’s aesthetic while gaining structured state management and attestation integration.
