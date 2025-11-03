"""
Proof-of-concept chat page wiring the reusable components together.
"""

from __future__ import annotations

import json
from pathlib import Path

import solara

from app.components.chat import attestation, backend, state, view

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATTESTATION_FILE = PROJECT_ROOT / "storage" / "attestation_state.json"
PROMPT_SUGGESTIONS_FILE = PROJECT_ROOT / "storage" / "prompt_suggestions.json"


def load_prompt_suggestions() -> dict[str, list[str]]:
    if PROMPT_SUGGESTIONS_FILE.exists():
        try:
            return json.loads(PROMPT_SUGGESTIONS_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


@solara.component
def Page():
    controller = solara.use_memo(
        lambda: state.ChatController(
            backend_client=backend.MockChatBackend(),
            attestation_store=attestation.FileAttestationStore(ATTESTATION_FILE),
            prompt_categories=load_prompt_suggestions(),
        ),
        [],
    )
    view.ChatSurface(controller)
