"""
components.py — Streamlit UI rendering helpers.
Keeps app.py clean by isolating all display logic here.
"""

import streamlit as st
from config import STARTER_QUESTIONS, APP_TITLE, APP_ICON, APP_SUBTITLE


def render_header():
    """Render the app title and subtitle."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="centered",
    )
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.caption(APP_SUBTITLE)
    st.divider()


def render_starter_questions():
    """
    Render clickable starter question buttons.
    Returns the question text if one is clicked, else None.
    """
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, question in enumerate(STARTER_QUESTIONS):
        col = cols[i % 2]
        if col.button(question, key=f"starter_{i}", use_container_width=True):
            return question
    return None


def render_route_badge(route: str, elapsed: float):
    """Render a small badge showing the route taken and response time."""
    route_colors = {
        "sql":    "🟦",
        "vector": "🟩",
        "both":   "🟨",
    }
    icon = route_colors.get(route, "⬜")
    st.caption(f"{icon} route: `{route}` · ⏱ {elapsed:.1f}s")


def render_sql_expander(sql: str):
    """Render the generated SQL inside a collapsible expander."""
    if sql:
        with st.expander("View generated SQL", expanded=False):
            st.code(sql, language="sql")


def render_dataframe(df):
    """Render the raw SQL results as a styled dataframe."""
    if df is not None and not df.empty:
        with st.expander("View raw results", expanded=False):
            st.dataframe(df, use_container_width=True)


def render_error(error: str):
    """Render an error message."""
    st.error(f"Something went wrong: {error}")


def render_chat_history(messages: list):
    """Render the full chat history."""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Re-render metadata for assistant messages
            if message["role"] == "assistant" and "meta" in message:
                meta = message["meta"]
                render_route_badge(meta.get("route", ""), meta.get("elapsed", 0))
                render_sql_expander(meta.get("sql"))
                render_dataframe(meta.get("dataframe"))