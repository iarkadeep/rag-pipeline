"""
Phase 2 — Script 3: Vector Retrieval
Embeds a user question with Gemini and retrieves the top matching
schema documents from ChromaDB.

Run standalone: python phase2/3_vector_retrieval.py
"""

import os
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

EMBED_MODEL = "models/gemini-embedding-001"
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "northwind_schema"


def get_collection():
    """Load the ChromaDB collection created in Phase 1."""
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return chroma_client.get_collection(COLLECTION_NAME)


def embed_query(question: str) -> list[float]:
    """Embed a user question using Gemini retrieval_query task type."""
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=question,
        task_type="retrieval_query",  # different from retrieval_document used in Phase 1
    )
    return result["embedding"]


def retrieve(question: str, n_results: int = 4) -> dict:
    """
    Retrieve top-n most relevant schema documents for a question.
    Returns dict with keys: documents, metadatas, scores
    """
    collection = get_collection()
    embedding = embed_query(question)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    # Convert cosine distance to similarity score (1 = perfect match)
    scores = [round(1 - d, 3) for d in results["distances"][0]]

    return {"documents": docs, "metadatas": metas, "scores": scores}


def format_context(retrieval_result: dict) -> str:
    """
    Combine retrieved docs into a single context string
    to inject into the SQL generation prompt.
    """
    return "\n\n---\n\n".join(retrieval_result["documents"])


def main():
    print("=== Phase 2 / Step 3: Vector Retrieval ===\n")

    test_questions = [
        "Who are the top 5 customers by revenue?",
        "What does AOV mean?",
        "Which products are low on stock?",
        "How is fulfillment time calculated?",
    ]

    for question in test_questions:
        print(f"Q: {question}")
        result = retrieve(question, n_results=3)

        for doc, meta, score in zip(
            result["documents"], result["metadatas"], result["scores"]
        ):
            print(f"  [{score:.3f}] type={meta['type']}  table={meta.get('table', '—')}")
            print(f"          {doc[:100].strip()}...")
        print()

    print("✅ Vector retrieval working.")
    print("   Next: run python phase2/4_pipeline.py")


if __name__ == "__main__":
    main()