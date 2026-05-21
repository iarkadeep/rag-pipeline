"""
Phase 2 — Script 4: Full Retrieval Pipeline
Wires together: query router → vector retrieval → SQL chain → answer generation.

This is the core ask() function the Streamlit UI will call in Phase 3.

Run: python phase2/4_pipeline.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from groq import Groq
from dotenv import load_dotenv

# Import from our Phase 2 modules
from query_router import classify_query
from sql_chain import run_sql_chain
from vector_retrieval import retrieve, format_context

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ANSWER_SYSTEM_PROMPT = """
You are a friendly analytics assistant explaining data results to a business user.

Given a user question and the query results, write a clear and concise answer.

RULES:
1. Lead with a direct one-sentence answer to the question
2. If there is tabular data, format it as a clean markdown table
3. Round all currency to 2 decimal places with a $ sign
4. If results are empty, say clearly that no data was found — do not guess
5. Do not mention SQL, databases, tables, or any technical details
6. Keep the tone professional but conversational
7. Add one insight or observation at the end if it adds value

The user is a business person, not a developer.
"""


def generate_answer(question: str, context: str) -> str:
    """Generate a plain-English answer from a question and retrieved context or SQL results."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question: {question}\n\nData:\n{context}",
            },
        ],
        temperature=0.3,   # slight creativity for natural language, not zero
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


def ask(question: str, verbose: bool = False) -> dict:
    """
    Main entry point for the RAG pipeline.

    Takes a plain-English question, routes it, retrieves context,
    generates SQL if needed, executes it, and returns a clean answer.

    Returns:
        {
            "question": str,
            "route": "sql" | "vector" | "both",
            "sql": str | None,
            "raw_results": str | None,
            "answer": str,
            "error": str | None,
        }
    """
    result = {
        "question": question,
        "route": None,
        "sql": None,
        "raw_results": None,
        "answer": None,
        "error": None,
    }

    # ── Step 1: Classify the query ────────────────────────────────────────────
    route = classify_query(question)
    result["route"] = route
    if verbose:
        print(f"  Route: {route}")

    # ── Step 2: Retrieve schema context from ChromaDB ─────────────────────────
    retrieval = retrieve(question, n_results=4)
    schema_context = format_context(retrieval)
    if verbose:
        print(f"  Retrieved {len(retrieval['documents'])} schema docs")

    # ── Step 3: SQL path ──────────────────────────────────────────────────────
    if route in ("sql", "both"):
        sql_result = run_sql_chain(question, schema_context)
        result["sql"] = sql_result["sql"]

        if sql_result["error"]:
            result["error"] = sql_result["error"]
            result["answer"] = (
                f"I wasn't able to retrieve that data. "
                f"Technical detail: {sql_result['error']}"
            )
            return result

        df = sql_result["dataframe"]
        if verbose:
            print(f"  SQL returned {len(df)} rows")

        # Convert dataframe to a readable string for the answer prompt
        if df.empty:
            raw_results = "The query returned no results."
        else:
            raw_results = df.to_string(index=False)

        result["raw_results"] = raw_results

        if route == "sql":
            # SQL only — answer from query results
            result["answer"] = generate_answer(question, raw_results)
            return result

    # ── Step 4: Vector path ───────────────────────────────────────────────────
    if route == "vector":
        # Answer purely from schema/glossary context
        result["answer"] = generate_answer(question, schema_context)
        return result

    # ── Step 5: Both paths — combine SQL results + schema context ─────────────
    if route == "both":
        combined_context = (
            f"Query results:\n{result['raw_results']}"
            f"\n\nAdditional context:\n{schema_context}"
        )
        result["answer"] = generate_answer(question, combined_context)
        return result

    return result


def main():
    print("=== Phase 2 / Step 4: Full Pipeline ===\n")

    questions = [
        "What is total revenue for 1997?",
        "Who are the top 5 customers by revenue?",
        "How many orders are unshipped?",
        "What does AOV mean?",
        "What is our best-selling product category and how is revenue calculated?",
    ]

    for question in questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print("-" * 60)

        result = ask(question, verbose=True)

        if result["sql"]:
            print(f"\nGenerated SQL:\n{result['sql']}")
        if result["raw_results"]:
            print(f"\nRaw results:\n{result['raw_results']}")

        print(f"\nAnswer:\n{result['answer']}")

    print(f"\n{'='*60}")
    print("✅ Phase 2 complete! Full pipeline working end to end.")
    print("   Next: Phase 3 — Streamlit UI")


if __name__ == "__main__":
    main()