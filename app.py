"""
app.py — Main Streamlit entry point.

Run: streamlit run app.py
"""

import time
import sys
import os
import streamlit as st

# Make phase2/ importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "phase2"))

from pipeline import ask
from components import (
    render_header,
    render_starter_questions,
    render_route_badge,
    render_sql_expander,
    render_dataframe,
    render_error,
    render_chat_history,
)

# ── Page setup ────────────────────────────────────────────────────────────────
render_header()

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_starters" not in st.session_state:
    st.session_state.show_starters = True

# ── Starter questions (shown only before first message) ───────────────────────
if st.session_state.show_starters:
    clicked_question = render_starter_questions()
    if clicked_question:
        st.session_state.pending_question = clicked_question
        st.session_state.show_starters = False
        st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────────
render_chat_history(st.session_state.messages)

# ── Handle a pending question from starter buttons ────────────────────────────
question = None

if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask a question about your sales data...")
if user_input:
    question = user_input
    st.session_state.show_starters = False

# ── Process question ──────────────────────────────────────────────────────────
if question:

    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Run the pipeline with a spinner
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            start = time.time()
            result = ask(question)
            elapsed = time.time() - start

        # Render the answer
        if result["error"]:
            render_error(result["error"])
            answer_text = f"Sorry, I ran into an error: {result['error']}"
        else:
            st.markdown(result["answer"])
            render_route_badge(result["route"], elapsed)
            render_sql_expander(result.get("sql"))
            render_dataframe(result.get("dataframe"))
            answer_text = result["answer"]

        # Persist to chat history with metadata for re-rendering
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_text,
            "meta": {
                "route":     result["route"],
                "elapsed":   elapsed,
                "sql":       result.get("sql"),
                "dataframe": result.get("dataframe"),
            },
        })

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("About")
    st.markdown(
        "This chatbot uses a **RAG pipeline** to answer questions "
        "about the Northwind sales database.\n\n"
        "**How it works:**\n"
        "1. Your question is classified as SQL, vector, or both\n"
        "2. Relevant schema docs are retrieved from ChromaDB\n"
        "3. An LLM generates SQL using that context\n"
        "4. SQL runs against PostgreSQL\n"
        "5. Results are summarised in plain English"
    )
    st.divider()

    st.header("Stats")
    st.metric("Questions asked", len([m for m in st.session_state.messages if m["role"] == "user"]))

    st.divider()

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.show_starters = True
        st.rerun()