"""Shared configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path


DATA_DIR = Path(os.getenv("RAG_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def get_openai_base_url() -> str | None:
    value = os.getenv("OPENAI_BASE_URL", "").strip()
    return value or None


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def get_openai_embedding_model() -> str:
    return (
        os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
        or "text-embedding-3-small"
    )


_PLACEHOLDER_KEYS = {
    "sk-your-key-here",
    "your-key-here",
    "changeme",
}


def is_fake_mode() -> bool:
    """Use local fake LLM/embeddings when key is missing, placeholder, or starts with 'test'."""
    key = get_openai_api_key()
    if not key:
        return True
    lower = key.lower()
    return lower.startswith("test") or lower in _PLACEHOLDER_KEYS
