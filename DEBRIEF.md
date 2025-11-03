# Debrief

## Architecture Highlights
- Chat surface is composed through `app/components/chat/view.py`, which layers deterministic layout primitives (`solara.Card`, fixed paddings) to keep containers mounted and avoid reflow.
- `ChatController` (`app/components/chat/state.py`) owns the reactive state bag (`ChatState`) and orchestrates backend calls, attestation persistence, and feedback submission. It exposes synchronous APIs so components can optimistically update UI while background tasks complete.
- Data contracts live in `app/components/chat/models.py`, giving typed blocks (text, table, image path, integer) and message metadata with generated code. Tests exercise these contracts directly.
- `MockChatBackend` (`app/components/chat/backend.py`) simulates a composite AI response, assembling heterogeneous blocks and code metadata without network calls. Static assets reside in `app/public/static`.
- Attestation storage is abstracted behind `AttestationStore`; the POC binds to `FileAttestationStore` targeting `storage/attestation_state.json`, while tests rely on the in-memory variant.

## Flicker & Reflow Mitigations
- Message ids remain stable from optimistic placeholder through completion (`ChatController._resolve_assistant`), so Reacton diffing updates the existing widget instead of replacing the row.
- The virtual list (`VirtualMessageList`) renders a fixed window of messages and reuses the same scroll container; older messages slide in via a "load earlier" button instead of splicing the DOM, preserving scroll position.
- Code panel toggling uses Vuetify expansion panels within a persistent `Card`, so expanding code blocks changes only the inner content height. CSS in `ChatSurface` keeps borders/padding constant to avoid layout jumps.
- Input toolbar and feedback dialogs stay mounted; visibility toggles rely on component state instead of element churn, preventing re-render cascades.

## Testing Summary
- `app/tests/test_chat_components.py` covers the PRD acceptance criteria: backend round-trips, code panel toggling stability, independent feedback submissions, and attestation persistence.
- `ruff check` and `pytest` both succeed locally (pytest runs in asyncio strict mode, ensuring async boundaries remain tight).
