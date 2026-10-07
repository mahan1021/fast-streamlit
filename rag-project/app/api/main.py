"""FastAPI application: /docs, /ask, /health."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.ask import LLMServiceError, ask
from app.core.ingest import (
    ALLOWED_EXTENSIONS,
    EmbeddingServiceError,
    InvalidDocumentError,
    ingest_file,
)
from app.core.store import DocumentNotFoundError, save_document


load_dotenv()

app = FastAPI(title="Simple RAG API", version="1.0.0")


class AskRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]


class DocsResponse(BaseModel):
    doc_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/docs", response_model=DocsResponse)
async def upload_document(file: UploadFile = File(...)) -> DocsResponse:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

    data = await file.read()
    try:
        chunks = ingest_file(filename, data)
        doc_id = save_document(filename, chunks)
    except InvalidDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmbeddingServiceError as exc:
        raise HTTPException(status_code=502, detail=f"Embedding service error: {exc}") from exc

    return DocsResponse(doc_id=doc_id)



@app.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty")

    doc_id = payload.doc_id.strip().strip("\"'")
    if not doc_id:
        raise HTTPException(status_code=400, detail="doc_id must not be empty")

    try:
        result = ask(doc_id, question)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}") from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    except EmbeddingServiceError as exc:
        raise HTTPException(status_code=502, detail=f"Embedding service error: {exc}") from exc

    return AskResponse(answer=result["answer"], sources=result["sources"])
