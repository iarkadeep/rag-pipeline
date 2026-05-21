"""
Phase 2 — Script 2: SQL Chain
Takes a user question + schema context, generates SQL via Groq, executes against PostgreSQL.

Run standalone: python phase2/2_sql_chain.py
"""

import os
import pandas as pd
from groq import Groq
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
engine = create_engine(os.getenv("DB_URL"))

SQL_SYSTEM_PROMPT = """
You are an expert SQL analyst for a sales database called Northwind.

RULES:
1. Write PostgreSQL-compatible SQL only
2. Always use table aliases (e.g. o for orders, od for order_details, c for customers)
3. For revenue, ALWAYS use: SUM(od.unit_price * od.quantity * (1 - od.discount))
4. Never use SELECT * — always name columns explicitly
5. Always add LIMIT 20 unless the user asks for all records
6. Return ONLY the raw SQL query — no explanation, no markdown, no backticks

COMMON MISTAKES TO AVOID:
- Do NOT use unit_price from products for revenue — always use order_details.unit_price
- Do NOT forget (1 - discount) when calculating revenue
- Do NOT join order_details directly to customers — always go through orders first
- Do NOT invent column names — only use columns listed in the schema context

SCHEMA CONTEXT:
{schema_context}
"""


def generate_sql(question: str, schema_context: str) -> str:
    """Generate a SQL query from a natural language question and schema context."""
    prompt = SQL_SYSTEM_PROMPT.format(schema_context=schema_context)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=500,
    )
    sql = response.choices[0].message.content.strip()
    # Strip markdown fences if the LLM adds them despite instructions
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def execute_sql(sql: str) -> tuple[pd.DataFrame | None, str | None]:
    """
    Execute SQL against PostgreSQL.
    Returns (dataframe, None) on success or (None, error_message) on failure.
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df, None
    except Exception as e:
        return None, str(e)


def run_sql_chain(question: str, schema_context: str) -> dict:
    """
    Full SQL chain: question → SQL → execute → return results.
    Returns a dict with keys: sql, dataframe, error
    """
    sql = generate_sql(question, schema_context)
    df, error = execute_sql(sql)
    return {"sql": sql, "dataframe": df, "error": error}


def main():
    print("=== Phase 2 / Step 2: SQL Chain ===\n")

    # Minimal schema context for standalone testing
    # In the full pipeline this comes from ChromaDB
    test_schema = """
    TABLE: orders
    - order_id, customer_id, employee_id, order_date, shipped_date, freight

    TABLE: order_details
    - order_id, product_id, unit_price, quantity, discount
    - Revenue = SUM(unit_price * quantity * (1 - discount))

    TABLE: customers
    - customer_id, company_name, country, city

    TABLE: products
    - product_id, product_name, category_id, unit_price, discontinued

    TABLE: categories
    - category_id, category_name
    """

    test_questions = [
        "What is total revenue for 1997?",
        "Who are the top 5 customers by revenue?",
        "How many orders are unshipped?",
    ]

    for question in test_questions:
        print(f"Q: {question}")
        result = run_sql_chain(question, test_schema)

        print(f"SQL:\n{result['sql']}\n")
        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            print(result["dataframe"].to_string(index=False))
        print("-" * 60)

    print("\n✅ SQL chain working.")
    print("   Next: run python phase2/3_vector_retrieval.py")


if __name__ == "__main__":
    main()