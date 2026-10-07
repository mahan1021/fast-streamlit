# Simple RAG (FastAPI + Streamlit)

Minimal Retrieval-Augmented Generation demo. Upload a PDF/TXT, ask questions, get answers with sources.

API keys are read only from environment variables (`OPENAI_API_KEY`, `OPENAI_BASE_URL`). If the key is empty or starts with `test`, the app runs in **fake mode** (no real OpenAI calls) — useful for local tests.

## Install

```bash
cd rag-project
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

Put your real key in `.env`, or leave a `test-...` key for fake mode.

## Run the API

From the `rag-project` folder:

```bash
uvicorn app.api.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Run Streamlit

In another terminal (same folder, venv active):

```bash
streamlit run app/ui/streamlit_app.py
```

## Example curl

Upload a text file:

```bash
curl -X POST "http://127.0.0.1:8000/docs" -F "file=@notes.txt"
```

Ask a question (replace `DOC_ID`):

```bash
curl -X POST "http://127.0.0.1:8000/ask" ^
  -H "Content-Type: application/json" ^
  -d "{\"doc_id\":\"DOC_ID\",\"question\":\"What is this document about?\"}"
```

macOS / Linux:

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"doc_id":"DOC_ID","question":"What is this document about?"}'
```

## Tests

```bash
pytest -q
```

Tests use fake mode (`OPENAI_API_KEY=test-...`) so they never call the real API.

## Endpoints

| Method | Path     | Description                          |
|--------|----------|--------------------------------------|
| GET    | /health  | `{"status":"ok"}`                    |
| POST   | /docs    | Upload PDF/TXT → `{doc_id}`          |
| POST   | /ask     | `{doc_id, question}` → answer+sources|
