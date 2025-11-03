# Data models used by the chat component library.

from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

MessageRole = Literal["user", "assistant", "system"]
MessageStatus = Literal["pending", "complete", "thinking"]
BlockType = Literal["text", "image", "table", "integer", "kv"]
_UTC = _dt.timezone.utc


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(_UTC)


def new_message_id() -> str:
    """Generate a stable unique identifier for messages."""
    return str(uuid.uuid4())


@dataclass(slots=True)
class MessagePart:
    """Single ordered fragment within a message block."""

    kind: BlockType
    text: Optional[str] = None
    image_path: Optional[str] = None
    table_rows: Optional[Sequence[Dict[str, Any]]] = None
    integer_value: Optional[int] = None
    kv_pairs: Optional[Sequence[Tuple[str, Any]]] = None


@dataclass(slots=True)
class MessageBlock:
    """Ordered group of fragments rendered together."""

    parts: List[MessagePart] = field(default_factory=list)

    @classmethod
    def single(cls, part: MessagePart) -> "MessageBlock":
        return cls(parts=[part])

    @classmethod
    def from_parts(cls, parts: Iterable[MessagePart]) -> "MessageBlock":
        return cls(parts=list(parts))


@dataclass(slots=True, kw_only=True)
class MessageMetadata:
    """Supplementary metadata attached to a message."""

    python_code: Optional[str] = None
    source: Optional[str] = None


@dataclass(slots=True)
class Message:
    """Chat message composed of ordered blocks."""

    id: str
    role: MessageRole
    blocks: List[MessageBlock] = field(default_factory=list)
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    status: MessageStatus = "complete"
    created_at: _dt.datetime = field(default_factory=utcnow)
    toolbar_collapsed: bool = True


@dataclass(slots=True)
class FeedbackDraft:
    """Mutable draft before submission."""

    minutes_saved: int = 0
    score: int = 5
    comments: str = ""


@dataclass(slots=True)
class FeedbackRecord(FeedbackDraft):
    """Submitted feedback with timestamp."""

    submitted_at: _dt.datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class AttestationState:
    """Tracks whether the user has passed the attestation gate."""

    required: bool = True
    accepted: bool = False
    last_accepted_at: Optional[_dt.datetime] = None


@dataclass(slots=True)
class ChatState:
    """Reactive state container for the chat experience."""

    messages: List[Message] = field(default_factory=list)
    pending_message_ids: List[str] = field(default_factory=list)
    attestation: AttestationState = field(default_factory=AttestationState)
    feedback_submissions: Dict[str, FeedbackRecord] = field(default_factory=dict)
    feedback_drafts: Dict[str, FeedbackDraft] = field(default_factory=dict)
    active_feedback_message_id: Optional[str] = None
    prompt_categories: Dict[str, List[str]] = field(default_factory=dict)

    def message_index(self, message_id: str) -> Optional[int]:
        for idx, msg in enumerate(self.messages):
            if msg.id == message_id:
                return idx
        return None
