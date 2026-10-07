"""Search stored chunks and call the LLM to answer a question."""

from __future__ import annotations

from typing import Any

from app.core.config import (
    get_openai_api_key,
    get_openai_base_url,
    get_openai_model,
    is_fake_mode,
)
from app.core.ingest import embed_texts
from app.core.store import search


class LLMServiceError(RuntimeError):
    """Raised when the LLM provider fails."""


def _build_context(chunks: list[dict[str, Any]]) -> str:
    return "\n\n".join(f"[{i + 1}] {chunk['text']}" for i, chunk in enumerate(chunks))


def _fake_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "No relevant context found in the document."
    snippets = " ".join(chunk["text"][:200] for chunk in chunks[:2])
    return (
        f"[fake] Based on the document, here is an answer to '{question}': {snippets}"
    )


def _openai_answer(question: str, context: str) -> str:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    kwargs: dict[str, Any] = {
        "api_key": get_openai_api_key(),
        "model": get_openai_model(),
        "temperature": 0,
    }
    base_url = get_openai_base_url()
    if base_url:
        kwargs["base_url"] = base_url

    llm = ChatOpenAI(**kwargs)
    messages = [
        SystemMessage(
            content=(
                "You are a helpful assistant. Answer the user's question using only "
                "the provided context. If the context is insufficient, say so."
            )
        ),
        HumanMessage(
            content=f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        ),
    ]
    try:
        response = llm.invoke(messages)
    except Exception as exc:  # noqa: BLE001
        raise LLMServiceError(str(exc)) from exc

    content = getattr(response, "content", None)
    if not content:
        raise LLMServiceError("Empty response from LLM")
    return str(content)


def ask(doc_id: str, question: str, top_k: int = 3) -> dict[str, Any]:
    """Return answer + source chunks for a question about a stored document."""
    query_embedding = embed_texts([question])[0]
    chunks = search(doc_id, query_embedding, top_k=top_k)
    context = _build_context(chunks)

    if is_fake_mode():
        answer = _fake_answer(question, chunks)
    else:
        answer = _openai_answer(question, context)

    sources = [{"text": c["text"], "score": c["score"]} for c in chunks]
    return {"answer": answer, "sources": sources}
