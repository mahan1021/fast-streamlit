"""Persist and retrieve document chunks on disk as JSON."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from app.core import config


class DocumentNotFoundError(KeyError):
    """Raised when a doc_id does not exist on disk."""


def _docs_dir() -> Path:
    path = Path(config.DATA_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _doc_path(doc_id: str) -> Path:
    return _docs_dir() / f"{doc_id}.json"


def save_document(filename: str, chunks: list[dict[str, Any]]) -> str:
    doc_id = str(uuid.uuid4())
    payload = {
        "doc_id": doc_id,
        "filename": filename,
        "chunks": chunks,
    }
    _doc_path(doc_id).write_text(json.dumps(payload), encoding="utf-8")
    return doc_id


def load_document(doc_id: str) -> dict[str, Any]:
    path = _doc_path(doc_id)
    if not path.exists():
        raise DocumentNotFoundError(doc_id)
    return json.loads(path.read_text(encoding="utf-8"))


def search(doc_id: str, query_embedding: list[float], top_k: int = 3) -> list[dict[str, Any]]:
    """Return top_k chunks by cosine similarity."""
    document = load_document(doc_id)
    query = np.array(query_embedding, dtype=np.float32)
    q_norm = np.linalg.norm(query)
    if q_norm == 0:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in document.get("chunks", []):
        vec = np.array(chunk["embedding"], dtype=np.float32)
        v_norm = np.linalg.norm(vec)
        if v_norm == 0:
            continue
        score = float(np.dot(query, vec) / (q_norm * v_norm))
        scored.append((score, {"text": chunk["text"], "score": score}))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]
