"""
config.py — Centralised settings for the RAG Analytics Chatbot.
Import this anywhere instead of repeating os.getenv() calls.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

# ── Database ──────────────────────────────────────────────────────────────────
DB_URL = os.getenv("DB_URL", "postgresql://localhost:5432/northwind")

# ── Models ────────────────────────────────────────────────────────────────────
EMBED_MODEL       = "models/gemini-embedding-001"
GENERATION_MODEL  = "gemini-1.5-flash"      # used for routing, SQL gen, answer gen

# ── Vector Store ──────────────────────────────────────────────────────────────
CHROMA_PATH      = "data/chroma_db"
COLLECTION_NAME  = "northwind_schema"

# ── Retrieval ─────────────────────────────────────────────────────────────────
TOP_K_RESULTS = 4       # number of schema docs to retrieve per query

# ── Generation ────────────────────────────────────────────────────────────────
MAX_TOKENS_SQL    = 500
MAX_TOKENS_ANSWER = 600
TEMPERATURE_ROUTE = 0.0
TEMPERATURE_SQL   = 0.0
TEMPERATURE_ANSWER = 0.3

# ── UI ────────────────────────────────────────────────────────────────────────
APP_TITLE    = "Northwind Analytics"
APP_ICON     = "📊"
APP_SUBTITLE = "Ask anything about your sales data in plain English."

STARTER_QUESTIONS = [
    "What is total revenue for 1997?",
    "Who are the top 5 customers by revenue?",
    "Which product category generates the most sales?",
    "How many orders are still unshipped?",
    "Which employee has generated the most revenue?",
    "What does AOV mean and what is ours?",
]