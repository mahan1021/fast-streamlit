"""Read PDF/TXT files, chunk text, and create embeddings."""

from __future__ import annotations

import hashlib
import io
from typing import Any

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.config import (
    get_openai_api_key,
    get_openai_base_url,
    get_openai_embedding_model,
    is_fake_mode,
)

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
EMBED_DIM = 64


class InvalidDocumentError(ValueError):
    """Raised when an uploaded file cannot be ingested."""


class EmbeddingServiceError(RuntimeError):
    """Raised when the embedding provider fails."""


def _read_txt(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InvalidDocumentError("Could not decode text file")


def _read_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        parts = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # noqa: BLE001 - surface as validation error
        raise InvalidDocumentError(f"Invalid PDF file: {exc}") from exc
    return "\n".join(parts)


def extract_text(filename: str, data: bytes) -> str:
    if not data:
        raise InvalidDocumentError("Uploaded file is empty")

    name = filename.lower()
    if name.endswith(".txt"):
        text = _read_txt(data)
    elif name.endswith(".pdf"):
        text = _read_pdf(data)
    else:
        raise InvalidDocumentError("Only PDF and TXT files are supported")

    text = text.strip()
    if not text:
        raise InvalidDocumentError("Document has no extractable text")
    return text


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    chunks = [c.strip() for c in splitter.split_text(text) if c.strip()]
    if not chunks:
        raise InvalidDocumentError("No chunks produced from document")
    return chunks


def _fake_embed(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand digest into a fixed-size deterministic vector.
        raw = np.frombuffer((digest * ((EMBED_DIM // len(digest)) + 1))[:EMBED_DIM], dtype=np.uint8)
        vec = raw.astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vectors.append(vec.tolist())
    return vectors


def _openai_embed(texts: list[str]) -> list[list[float]]:
    from langchain_openai import OpenAIEmbeddings

    kwargs: dict[str, Any] = {
        "api_key": get_openai_api_key(),
        "model": get_openai_embedding_model(),
    }
    base_url = get_openai_base_url()
    if base_url:
        kwargs["base_url"] = base_url

    embeddings = OpenAIEmbeddings(**kwargs)
    try:
        return embeddings.embed_documents(texts)
    except Exception as exc:  # noqa: BLE001
        raise EmbeddingServiceError(str(exc)) from exc



def embed_texts(texts: list[str]) -> list[list[float]]:
    if is_fake_mode():
        return _fake_embed(texts)
    return _openai_embed(texts)


def ingest_file(filename: str, data: bytes) -> list[dict[str, Any]]:
    """Return chunk dicts with text + embedding ready for storage."""
    text = extract_text(filename, data)
    chunks = chunk_text(text)
    vectors = embed_texts(chunks)
    return [{"text": chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]
