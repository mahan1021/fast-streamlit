"""Streamlit UI — talks only to the FastAPI backend via HTTP."""

from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE = os.getenv("RAG_API_BASE", "http://127.0.0.1:8000")


st.set_page_config(page_title="Simple RAG", page_icon=None, layout="centered")
st.title("Simple RAG")
st.caption(f"Backend: {API_BASE}")


def api_health() -> bool:
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except requests.RequestException:
        return False


if api_health():
    st.success("API is healthy")
else:
    st.error("API is not reachable. Start it with: uvicorn app.api.main:app --reload")

if "doc_id" not in st.session_state:
    st.session_state.doc_id = ""

st.subheader("1. Upload a document")
uploaded = st.file_uploader("PDF or TXT", type=["pdf", "txt"])

if uploaded is not None and st.button("Ingest document"):
    files = {"file": (uploaded.name, uploaded.getvalue())}
    try:
        response = requests.post(f"{API_BASE}/docs", files=files, timeout=120)
        if response.status_code == 200:
            st.session_state.doc_id = response.json()["doc_id"]
            st.success(f"Uploaded: {uploaded.name}")
        else:
            st.error(f"Upload failed ({response.status_code}): {response.text}")
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")

if st.session_state.doc_id:
    st.info("Document ready — ask a question below.")

st.subheader("2. Ask a question")
question = st.text_area("Question", placeholder="What is this document about?")

if st.button("Ask"):
    if not st.session_state.doc_id:
        st.warning("Upload a document first.")
    elif not question.strip():
        st.warning("Question must not be empty.")
    else:
        try:
            response = requests.post(
                f"{API_BASE}/ask",
                json={"doc_id": st.session_state.doc_id, "question": question.strip()},
                timeout=120,
            )
            if response.status_code == 200:
                payload = response.json()
                st.markdown("### Answer")
                st.write(payload["answer"])
                st.markdown("### Sources")
                for i, source in enumerate(payload.get("sources", []), start=1):
                    score = source.get("score")
                    label = f"Source {i}" + (f" (score={score:.3f})" if score is not None else "")
                    st.markdown(f"**{label}**")
                    st.write(source.get("text", ""))
            else:
                st.error(f"Ask failed ({response.status_code}): {response.text}")
        except requests.RequestException as exc:
            st.error(f"Request failed: {exc}")
