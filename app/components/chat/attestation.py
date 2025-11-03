# Attestation storage and provider helpers.

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class AttestationStore(ABC):
    """Abstract persistence boundary for the attestation gate."""

    @abstractmethod
    def read(self) -> Optional[bool]:
        """Return the persisted acceptance state if known."""

    @abstractmethod
    def write(self, accepted: bool) -> None:
        """Persist the acceptance decision."""


class FileAttestationStore(AttestationStore):
    """File backed implementation used for the POC."""

    def __init__(self, path: Path):
        self.path = path

    def read(self) -> Optional[bool]:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return None
        accepted = payload.get("accepted")
        if isinstance(accepted, bool):
            return accepted
        return None

    def write(self, accepted: bool) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"accepted": accepted}))


class MemoryAttestationStore(AttestationStore):
    """In-memory store handy for tests."""

    def __init__(self, initial: Optional[bool] = None):
        self._accepted = initial

    def read(self) -> Optional[bool]:
        return self._accepted

    def write(self, accepted: bool) -> None:
        self._accepted = accepted
