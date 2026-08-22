import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
DEFAULT_REALTIME_MODEL = "gpt-4o-realtime-preview"


@dataclass(frozen=True)
class RealtimeCallResult:
    sdp_answer: str
    openai_call_id: str
    location_header: str


class RealtimeClient:
    def create_call(
        self,
        *,
        sdp_offer: str,
        session_config: dict[str, Any],
        safety_identifier: str,
    ) -> RealtimeCallResult:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        files = {
            "sdp": (None, sdp_offer.encode("utf-8"), "application/sdp"),
            "session": (
                None,
                json.dumps(session_config).encode("utf-8"),
                "application/json",
            ),
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Safety-Identifier": safety_identifier,
            "Accept": "application/sdp",
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(REALTIME_CALLS_URL, headers=headers, files=files)
            response.raise_for_status()

        location = response.headers.get("Location", "")
        openai_call_id = _extract_call_id(location)
        if not openai_call_id:
            raise RuntimeError("OpenAI Realtime response missing call id in Location header")

        return RealtimeCallResult(
            sdp_answer=response.text,
            openai_call_id=openai_call_id,
            location_header=location,
        )


_client_factory: Callable[[], RealtimeClient] | None = None


def set_realtime_client_factory(factory: Callable[[], RealtimeClient] | None) -> None:
    global _client_factory
    _client_factory = factory


def get_realtime_client() -> RealtimeClient:
    if _client_factory is not None:
        return _client_factory()
    return RealtimeClient()


def get_configured_realtime_model() -> str:
    return os.environ.get("OPENAI_REALTIME_MODEL", DEFAULT_REALTIME_MODEL)


def _extract_call_id(location_header: str) -> str:
    if not location_header:
        return ""
    path = urlparse(location_header).path or location_header
    return path.rstrip("/").split("/")[-1]
