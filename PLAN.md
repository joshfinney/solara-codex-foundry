# PLAN

## Architecture
- `app/components/chat/` packaged as Solara components: `models.py` (message + block dataclasses), `store.py` (chat state + actions), `list.py` (virtualised message list with stable keys), `message.py` (render message blocks + toolbar), `input.py`, `attestation.py` (gate + provider), `feedback.py` (modal + state), `backend.py` (mock service contracts), `__init__.py` exposing public API.
- State flow relies on Solara reactive primitives (`solara.Reactive`, `use_state`, `use_task`) with a single store responsible for optimistic sends, streamed updates, and gating/feedback status.
- Rendering keeps layout containers fixed (`solara.Column` with `style={"minHeight": ...}`), message list keyed by message id, expandable code panel using CSS `height` transitions with `overflow` control to avoid reflow.
- Attestation provider backed by `storage/attestation_state.json` via pluggable storage protocol (`AttestationStore` with file-based impl and future-proof hook).
- Mock server surface under `servers/mock_backend.py` (FastAPI) to simulate send/receive; Solara page interacts through async client defined in components backend.

## Deliverables
- `docs/solara-notes/*.md` capturing Solara internals (lifecycles, store primitives, rendering, list stability, long-list/streaming patterns) with cross-links.
- Chat component library scaffolding under `app/components/chat/` with tests under `app/tests/test_chat_components.py`.
- POC page `app/src/chat.py` wiring attestation, message list, input, and mock backend interaction.
- Feedback modal + attestation gate integrated into component library with persistent store.
- Mock backend + fixtures delivering composite messages used by components and tests.
- Acceptance-aligned tests (component level + attestation behavior) using Solara/pytest without flaky sleeps.
- Updated documentation: `DEBRIEF.md` detailing design decisions and flicker mitigation; instructions in README if needed.
- Repo lint/test scripts executed (`ruff`, `pytest`), issues fixed, final commit prepared (pending user direction).
