"""HTTP clients prepared for a future FastAPI migration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class FastAPIResponse:
    status_code: int
    payload: Dict[str, Any]

    @classmethod
    def from_response(cls, response: httpx.Response) -> "FastAPIResponse":
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"raw": response.text}
        return cls(status_code=response.status_code, payload=data)


class FastAPIClient:
    """Minimal wrapper around httpx for future service calls."""

    def __init__(self, base_url: str, *, timeout: float = 10.0, session: Optional[httpx.Client] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = session or httpx.Client(timeout=timeout)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> FastAPIResponse:
        url = f"{self._base_url}/{path.lstrip('/')}"
        response = self._session.get(url, params=params)
        return FastAPIResponse.from_response(response)

    def post(self, path: str, payload: Dict[str, Any]) -> FastAPIResponse:
        url = f"{self._base_url}/{path.lstrip('/')}"
        response = self._session.post(url, json=payload)
        return FastAPIResponse.from_response(response)

    def close(self) -> None:
        self._session.close()
