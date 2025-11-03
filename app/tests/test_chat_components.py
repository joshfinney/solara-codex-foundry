from app.components.chat import attestation, backend, models, state


def make_controller(initial_attested: bool | None = True):
    store = attestation.MemoryAttestationStore(initial=initial_attested)
    controller = state.ChatController(backend.MockChatBackend(delay_seconds=0.0), store)
    return controller, store


def assistant_messages(chat_state: models.ChatState):
    return [message for message in chat_state.messages if message.role == "assistant"]


def test_round_trip_generates_composite_message():
    controller, _ = make_controller()
    controller.send_user_message("Hello world")
    chat_state = controller.state.value
    assert len(chat_state.messages) == 2
    assistant = assistant_messages(chat_state)[0]
    parts = [part for block in assistant.blocks for part in block.parts]
    kinds = {part.kind for part in parts}
    assert {"text", "integer", "table", "image", "kv"} <= kinds
    kv_part = next(part for part in parts if part.kind == "kv")
    assert [key for key, _ in kv_part.kv_pairs] == ["Prompt length", "Word count", "Preview"]
    assert [part.kind for part in parts] == ["text", "integer", "kv", "table", "image"]
    assert assistant.status == "complete"
    assert not chat_state.pending_message_ids


def test_code_panel_toggle_preserves_order():
    controller, _ = make_controller()
    controller.send_user_message("toggle code please")
    chat_state = controller.state.value
    before_ids = [msg.id for msg in chat_state.messages]
    assistant = assistant_messages(chat_state)[0]
    assert assistant.toolbar_collapsed

    controller.toggle_code_panel(assistant.id)
    chat_state_after = controller.state.value
    after_ids = [msg.id for msg in chat_state_after.messages]
    assert before_ids == after_ids
    updated_assistant = assistant_messages(chat_state_after)[0]
    assert updated_assistant.toolbar_collapsed is False


def test_feedback_submissions_are_per_message():
    controller, _ = make_controller()
    controller.send_user_message("first prompt")
    controller.send_user_message("second prompt")
    chat_state = controller.state.value
    assistants = assistant_messages(chat_state)
    assert len(assistants) == 2
    first, second = assistants

    controller.toggle_feedback_panel(first.id)
    controller.update_feedback_draft(
        first.id, lambda draft: models.FeedbackDraft(minutes_saved=5, score=8, comments="Great!")
    )
    controller.submit_feedback(first.id)

    controller.toggle_feedback_panel(second.id)
    controller.update_feedback_draft(
        second.id, lambda draft: models.FeedbackDraft(minutes_saved=2, score=4, comments="Needs work")
    )

    updated_state = controller.state.value
    assert first.id in updated_state.feedback_submissions
    assert second.id not in updated_state.feedback_submissions
    assert second.id in updated_state.feedback_drafts
    assert updated_state.feedback_submissions[first.id].minutes_saved == 5
    assert updated_state.feedback_drafts[second.id].comments == "Needs work"


def test_attestation_persistence():
    controller, store = make_controller(initial_attested=None)
    chat_state = controller.state.value
    assert chat_state.attestation.required
    controller.record_attestation(True)
    updated_state = controller.state.value
    assert updated_state.attestation.accepted
    assert updated_state.attestation.required is False
    assert store.read() is True
