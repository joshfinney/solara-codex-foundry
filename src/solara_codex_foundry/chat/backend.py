# Mock and real backend contracts for chat responses.

from __future__ import annotations

import asyncio
import random
from typing import Protocol, Sequence

from . import models


class ChatBackend(Protocol):
    """Backend interface that returns assistant messages for a chat history."""

    async def respond(self, history: Sequence[models.Message]) -> models.Message: ...


class MockChatBackend:
    """Deterministic mock used by the POC page and tests."""

    def __init__(self, delay_seconds: float = 0.15):
        self.delay_seconds = delay_seconds
        self._image_choices = [
            "/static/bot.png",
            "/static/chart.png",
        ]

    async def respond(self, history: Sequence[models.Message]) -> models.Message:
        await asyncio.sleep(self.delay_seconds)
        latest_user = next((m for m in reversed(history) if m.role == "user"), None)
        prompt = ""
        if latest_user:
            text_blocks = [
                part.text
                for block in latest_user.blocks
                for part in block.parts
                if part.kind == "text" and part.text
            ]
            prompt = " ".join(text_blocks)
        rows = [
            {"step": "Prompt length", "value": len(prompt)},
            {"step": "Words detected", "value": len(prompt.split()) if prompt else 0},
        ]
        assistant_id = models.new_message_id()
        summary_pairs = [
            ("Prompt length", len(prompt)),
            ("Word count", len(prompt.split()) if prompt else 0),
            ("Preview", prompt[:48]),
        ]
        blocks = [
            models.MessageBlock.from_parts(
                [
                    models.MessagePart(kind="text", text=f"Echoing your request: {prompt or 'No prompt provided.'}"),
                    models.MessagePart(kind="integer", integer_value=len(prompt)),
                    models.MessagePart(kind="kv", kv_pairs=summary_pairs),
                    models.MessagePart(kind="table", table_rows=rows),
                    models.MessagePart(kind="image", image_path=random.choice(self._image_choices)),
                ]
            )
        ]
        metadata = models.MessageMetadata(
            python_code="\n".join(
                [
                    "def generate_response(prompt: str) -> dict:",
                    "    tokens = prompt.split()",
                    "    return {",
                    "        'length': len(prompt),",
                    "        'words': len(tokens),",
                    "        'preview': prompt[:64],",
                    "    }",
                ]
            )
        )
        return models.Message(
            id=assistant_id,
            role="assistant",
            blocks=blocks,
            metadata=metadata,
            status="complete",
        )
