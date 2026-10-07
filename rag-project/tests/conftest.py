"""Pytest fixtures for the RAG API."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Force fake/test mode before importing the app.
os.environ["OPENAI_API_KEY"] = "test-key-for-pytest"
os.environ.pop("OPENAI_BASE_URL", None)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-pytest")

    import app.core.config as config

    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")

    from app.api.main import app

    with TestClient(app) as test_client:
        yield test_client
