"""Reactive chat controller orchestrating backend, attestation, and feedback flows."""

from __future__ import annotations

import asyncio
import dataclasses
import datetime as _dt
from typing import Callable, Dict, List, Optional

import solara

from app.models import chat as chat_models
from app.services import attestation as attestation_service
from app.services import chat_backend


class ChatController:
    """High-level orchestrator for chat interactions."""

    def __init__(
        self,
        *,
        backend_client: chat_backend.ChatBackend,
        attestation_store: attestation_service.AttestationStore,
        prompt_categories: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self._backend = backend_client
        self._attestation_store = attestation_store
        attested = attestation_store.read()
        attestation_state = chat_models.AttestationState(
            required=attested is None or attested is False,
            accepted=bool(attested),
            last_accepted_at=None,
        )
        if attestation_state.accepted:
            attestation_state.required = False
        initial_state = chat_models.ChatState(
            attestation=attestation_state,
            prompt_categories=prompt_categories or {},
        )
        self.state: solara.Reactive[chat_models.ChatState] = solara.reactive(initial_state)

    # ------------------------------------------------------------------ Attestation
    def record_attestation(self, accepted: bool) -> None:
        now = _dt.datetime.now(_dt.timezone.utc)

        def updater(prev: chat_models.ChatState):
            att = dataclasses.replace(
                prev.attestation,
                required=not accepted,
                accepted=accepted,
                last_accepted_at=now if accepted else None,
            )
            return {"attestation": att}

        self.state.update(updater)
        self._attestation_store.write(accepted)

    # ------------------------------------------------------------------ Messaging
    def send_user_message(self, text: str):
        text = text.strip()
        if not text:
            return
        user_message = chat_models.Message(
            id=chat_models.new_message_id(),
            role="user",
            blocks=[
                chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="text", text=text),
                )
            ],
            status="complete",
        )
        assistant_id = chat_models.new_message_id()
        placeholder = chat_models.Message(
            id=assistant_id,
            role="assistant",
            blocks=[
                chat_models.MessageBlock.single(
                    chat_models.MessagePart(kind="text", text="Thinking…"),
                )
            ],
            status="thinking",
            toolbar_collapsed=True,
        )

        history_for_backend = [*self.state.value.messages, user_message]

        def enqueue(prev: chat_models.ChatState):
            messages = [*prev.messages, user_message, placeholder]
            pending = [*prev.pending_message_ids, assistant_id]
            return {"messages": messages, "pending_message_ids": pending}

        self.state.update(enqueue)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            asyncio.run(self._resolve_assistant(assistant_id, history_for_backend))
            return None

        return loop.create_task(self._resolve_assistant(assistant_id, history_for_backend))

    async def _resolve_assistant(
        self, assistant_id: str, history_for_backend: list[chat_models.Message]
    ) -> None:
        try:
            assistant_message = await self._backend.respond(history_for_backend)
            final_message = dataclasses.replace(assistant_message, id=assistant_id, status="complete")
        except Exception as error:  # noqa: BLE001
            final_message = chat_models.Message(
                id=assistant_id,
                role="assistant",
                status="complete",
                blocks=[
                    chat_models.MessageBlock.from_parts(
                        [
                            chat_models.MessagePart(
                                kind="text", text="Sorry, something went wrong."
                            ),
                            chat_models.MessagePart(kind="text", text=str(error)),
                        ]
                    )
                ],
            )

        def resolve(prev: chat_models.ChatState):
            messages = list(prev.messages)
            idx = prev.message_index(assistant_id)
            if idx is not None:
                messages[idx] = final_message
            pending = [mid for mid in prev.pending_message_ids if mid != assistant_id]
            return {"messages": messages, "pending_message_ids": pending}

        self.state.update(resolve)

    # ------------------------------------------------------------------ Toolbar + feedback helpers
    def toggle_code_panel(self, message_id: str) -> None:
        def updater(prev: chat_models.ChatState):
            idx = prev.message_index(message_id)
            if idx is None:
                return {}
            messages = list(prev.messages)
            current = messages[idx]
            messages[idx] = dataclasses.replace(current, toolbar_collapsed=not current.toolbar_collapsed)
            return {"messages": messages}

        self.state.update(updater)

    def toggle_feedback_panel(self, message_id: str) -> None:
        def updater(prev: chat_models.ChatState):
            current = prev.active_feedback_message_id
            new_active = None if current == message_id else message_id
            return {"active_feedback_message_id": new_active}

        self.state.update(updater)

    def update_feedback_draft(
        self,
        message_id: str,
        mutator: Callable[[chat_models.FeedbackDraft], chat_models.FeedbackDraft],
    ) -> None:
        def updater(prev: chat_models.ChatState):
            drafts = dict(prev.feedback_drafts)
            draft = drafts.get(message_id, chat_models.FeedbackDraft())
            drafts[message_id] = mutator(draft)
            return {"feedback_drafts": drafts}

        self.state.update(updater)

    def submit_feedback(self, message_id: str) -> None:
        draft = self.state.value.feedback_drafts.get(message_id)
        if draft is None:
            return
        record = chat_models.FeedbackRecord(
            minutes_saved=draft.minutes_saved,
            score=draft.score,
            comments=draft.comments,
        )

        def updater(prev: chat_models.ChatState):
            submissions = dict(prev.feedback_submissions)
            submissions[message_id] = record
            drafts = dict(prev.feedback_drafts)
            drafts.pop(message_id, None)
            active_id = prev.active_feedback_message_id
            if active_id == message_id:
                active_id = None
            payload = {
                "feedback_submissions": submissions,
                "feedback_drafts": drafts,
                "active_feedback_message_id": active_id,
            }
            return payload

        self.state.update(updater)

