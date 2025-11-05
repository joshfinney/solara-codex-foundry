"""
Proof-of-concept chat page wiring the reusable components together.
"""

from __future__ import annotations

import json
from pathlib import Path

import solara

from app.services import attestation, chat_backend
from app.state import ChatController
from app.ui import chat as chat_view

PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
        lambda: ChatController(
            backend_client=chat_backend.MockChatBackend(),
            attestation_store=attestation.FileAttestationStore(ATTESTATION_FILE),
            prompt_categories=load_prompt_suggestions(),
        ),
        [],
    )
    chat_view.ChatSurface(controller)
