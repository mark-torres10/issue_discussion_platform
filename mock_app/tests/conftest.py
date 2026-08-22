"""Shared pytest fixtures for mock_app API tests."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import PROFILES_JSON
from app.main import app
from app.services import data_store


@pytest.fixture
def tmp_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy profiles.json to a temp file with empty swipes; isolate the data store."""
    dest = tmp_path / "profiles.json"
    data = json.loads(PROFILES_JSON.read_text(encoding="utf-8"))
    data["swipes"] = []
    dest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    store = data_store.DataStore(dest)
    monkeypatch.setattr(data_store, "_store", store)
    yield dest


@pytest.fixture
def client(tmp_data_file: Path) -> TestClient:
    """FastAPI test client with an isolated data store."""
    return TestClient(app)
