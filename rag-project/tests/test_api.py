"""API tests — run in fake/test mode (no real OpenAI calls)."""

from __future__ import annotations

from io import BytesIO


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_valid_txt(client):
    content = b"Python is a programming language used for data science and AI."
    response = client.post(
        "/docs",
        files={"file": ("notes.txt", BytesIO(content), "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "doc_id" in payload
    assert payload["doc_id"]


def test_upload_invalid_extension(client):
    response = client.post(
        "/docs",
        files={"file": ("image.png", BytesIO(b"not-a-document"), "image/png")},
    )
    assert response.status_code == 400


def test_upload_empty_file(client):
    response = client.post(
        "/docs",
        files={"file": ("empty.txt", BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 400


def test_ask_empty_question(client):
    upload = client.post(
        "/docs",
        files={"file": ("notes.txt", BytesIO(b"Some content about cats."), "text/plain")},
    )
    doc_id = upload.json()["doc_id"]

    response = client.post("/ask", json={"doc_id": doc_id, "question": "   "})
    assert response.status_code == 400


def test_ask_missing_doc(client):
    response = client.post(
        "/ask",
        json={"doc_id": "does-not-exist", "question": "What is this?"},
    )
    assert response.status_code == 404


def test_ask_success(client):
    text = (
        b"The capital of France is Paris. "
        b"Paris is known for the Eiffel Tower and the Louvre museum."
    )
    upload = client.post(
        "/docs",
        files={"file": ("france.txt", BytesIO(text), "text/plain")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["doc_id"]

    response = client.post(
        "/ask",
        json={"doc_id": doc_id, "question": "What is the capital of France?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert payload["answer"]
    assert "sources" in payload
    assert isinstance(payload["sources"], list)
    assert len(payload["sources"]) > 0
