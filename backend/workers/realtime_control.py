"""Realtime sideband control worker for staging.

Run as a separate process:

    INTERNAL_WORKER_TOKEN=... OPENAI_API_KEY=... \\
        uv run python -m workers.realtime_control
"""

from __future__ import annotations

import logging
import os
import sys
import time

import httpx

from app.services.realtime import ControlHandoff, drain_control_handoff_queue

logger = logging.getLogger(__name__)


def process_control_handoff(handoff: ControlHandoff) -> None:
    """Staging stub: log handoff and optionally forward mock provider items."""
    logger.info(
        "control handoff received session_id=%s openai_call_id=%s",
        handoff.session_id,
        handoff.openai_call_id,
    )


def run_worker(*, poll_interval_seconds: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO)
    if not os.environ.get("INTERNAL_WORKER_TOKEN"):
        logger.error("INTERNAL_WORKER_TOKEN is required")
        sys.exit(1)

    logger.info("realtime control worker started")
    while True:
        for handoff in drain_control_handoff_queue():
            process_control_handoff(handoff)
        time.sleep(poll_interval_seconds)


def post_provider_item(
    *,
    base_url: str,
    openai_call_id: str,
    provider_item_id: str,
    display_text: str,
) -> dict[str, object]:
    """Helper for tests and staging to post a provider item via internal ingest."""
    token = os.environ.get("INTERNAL_WORKER_TOKEN")
    if not token:
        raise RuntimeError("INTERNAL_WORKER_TOKEN is not set")

    url = f"{base_url.rstrip('/')}/internal/v1/realtime/calls/{openai_call_id}/items"
    response = httpx.post(
        url,
        headers={"X-Worker-Token": token},
        json={
            "provider_item_id": provider_item_id,
            "display_text": display_text,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    run_worker()


if __name__ == "__main__":
    main()
