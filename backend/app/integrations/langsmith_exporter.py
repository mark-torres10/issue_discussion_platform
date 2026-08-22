"""LangSmith trace exporters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from app.integrations.langsmith_envelope import (
    envelope_to_metadata,
    validate_metadata,
)
from app.models.tracing import TraceEnvelope, TraceExportKind

logger = logging.getLogger(__name__)


class LangSmithRunClient(Protocol):
    """Minimal LangSmith client surface used for trace export."""

    def create_run(self, *, run_id: UUID, payload: dict[str, Any]) -> None: ...


@dataclass
class RecordingLangSmithClient:
    """Test double that records exported runs."""

    runs: list[dict[str, Any]] = field(default_factory=list)
    should_raise: bool = False

    def create_run(self, *, run_id: UUID, payload: dict[str, Any]) -> None:
        if self.should_raise:
            raise RuntimeError("LangSmith unavailable")
        self.runs.append({"run_id": run_id, **payload})


_langsmith_client_factory: LangSmithRunClient | None = None


def set_langsmith_client_factory(factory: LangSmithRunClient | None) -> None:
    """Replace the default LangSmith client, typically in tests."""
    global _langsmith_client_factory
    _langsmith_client_factory = factory


def get_langsmith_client() -> LangSmithRunClient:
    """Return a LangSmith client, honoring any injected test double."""
    if _langsmith_client_factory is not None:
        return _langsmith_client_factory
    from langsmith import Client

    class _ClientAdapter:
        def __init__(self) -> None:
            self._client = Client()

        def create_run(self, *, run_id: UUID, payload: dict[str, Any]) -> None:
            self._client.create_run(id=str(run_id), **payload)

    return _ClientAdapter()


class TraceExporter(Protocol):
    """Exports study trace envelopes to an observability backend."""

    def export_conversation_turn(self, envelope: TraceEnvelope) -> None: ...

    def export_lifecycle(
        self, envelope: TraceEnvelope, *, lifecycle_event: str
    ) -> None: ...

    def export_connection_failure(
        self, envelope: TraceEnvelope, *, event_type: str
    ) -> None: ...


class NoopExporter:
    """Discards trace exports when LangSmith is disabled."""

    def export_conversation_turn(self, envelope: TraceEnvelope) -> None:
        return None

    def export_lifecycle(
        self, envelope: TraceEnvelope, *, lifecycle_event: str
    ) -> None:
        return None

    def export_connection_failure(
        self, envelope: TraceEnvelope, *, event_type: str
    ) -> None:
        return None


class LangSmithExporter:
    """Posts allowlisted trace envelopes to LangSmith as chain runs."""

    def __init__(self, client: LangSmithRunClient, *, project_name: str) -> None:
        self._client = client
        self._project_name = project_name

    def _post(self, envelope: TraceEnvelope, *, run_type: str, name: str) -> None:
        metadata = envelope_to_metadata(envelope)
        validate_metadata(metadata)
        payload: dict[str, Any] = {
            "name": name,
            "run_type": run_type,
            "project_name": self._project_name,
            "inputs": envelope.approved_inputs,
            "outputs": envelope.approved_outputs,
            "extra": {"metadata": metadata},
        }
        if envelope.usage is not None:
            payload["usage_metadata"] = envelope.usage
        self._client.create_run(run_id=envelope.langsmith_run_id, payload=payload)

    def export_conversation_turn(self, envelope: TraceEnvelope) -> None:
        """Export a canonical conversation turn trace."""
        self._post(
            envelope,
            run_type="chain",
            name=TraceExportKind.conversation_turn.value,
        )

    def export_lifecycle(
        self, envelope: TraceEnvelope, *, lifecycle_event: str
    ) -> None:
        """Export a session lifecycle trace with the given event name."""
        metadata = envelope_to_metadata(envelope)
        metadata["lifecycle_event"] = lifecycle_event
        validate_metadata(metadata)
        payload: dict[str, Any] = {
            "name": TraceExportKind.session_lifecycle.value,
            "run_type": "chain",
            "project_name": self._project_name,
            "inputs": envelope.approved_inputs,
            "outputs": envelope.approved_outputs,
            "extra": {"metadata": metadata},
        }
        self._client.create_run(run_id=envelope.langsmith_run_id, payload=payload)

    def export_connection_failure(
        self, envelope: TraceEnvelope, *, event_type: str
    ) -> None:
        """Export a realtime connection failure trace."""
        self._post(
            envelope,
            run_type="chain",
            name=TraceExportKind.connection_failure.value,
        )


def build_exporter(*, enabled: bool, project_name: str) -> TraceExporter:
    """Return a LangSmith exporter or a no-op implementation."""
    if not enabled:
        return NoopExporter()
    return LangSmithExporter(get_langsmith_client(), project_name=project_name)
