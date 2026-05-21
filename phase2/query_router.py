"""
Phase 2 — Script 1: Query Router
Classifies a user question as: sql, vector, or both.
Uses Groq (Llama 3.1 70B) — free tier.

Run: python phase2/1_query_router.py
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ROUTER_SYSTEM_PROMPT = """
You are a query classifier for a sales analytics chatbot built on the Northwind database.

Given a user question, classify it into exactly one of these categories:

- sql     → needs specific numbers, counts, rankings, totals, comparisons,
            or any question answerable by querying a database
- vector  → needs definitions, explanations, how-to guidance, or
            descriptions of business terms and concepts
- both    → needs a database query AND contextual explanation together

Reply with ONLY the single word: sql, vector, or both.
No explanation. No punctuation. No other text.

Examples:
"What is total revenue in 1997?" → sql
"Who are the top 5 customers by revenue?" → sql
"What does AOV mean?" → vector
"How is revenue calculated?" → vector
"What is our best category and how is revenue calculated?" → both
"Show me unshipped orders and explain what that means?" → both
"""


def classify_query(question: str) -> str:
    """
    Classify a user question as 'sql', 'vector', or 'both'.
    Returns one of those three strings.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,        # deterministic — we want the same answer every time
        max_tokens=5,         # we only need one word back
    )
    result = response.choices[0].message.content.strip().lower()

    # Safety net: if the LLM returns something unexpected, default to both
    if result not in ("sql", "vector", "both"):
        print(f"  Warning: unexpected router output '{result}', defaulting to 'both'")
        return "both"

    return result


def main():
    print("=== Phase 2 / Step 1: Query Router ===\n")

    test_questions = [
        "What is total revenue for 1997?",
        "Who are the top 5 customers by revenue?",
        "What does AOV mean?",
        "How is revenue calculated in this database?",
        "Which employee has sold the most and what is their title?",
        "What are unshipped orders?",
        "How many products are discontinued?",
        "What is the reorder level?",
    ]

    print(f"{'Question':<55} {'Route'}")
    print("-" * 65)
    for q in test_questions:
        route = classify_query(q)
        print(f"{q:<55} {route}")

    print("\n✅ Query router working.")
    print("   Next: run python phase2/2_sql_chain.py")


if __name__ == "__main__":
    main()