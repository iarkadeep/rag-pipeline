"""
Phase 1 — Script 3 (Gemini version): Embed schema documents and store in ChromaDB.

Uses Google Gemini gemini-embedding-001 (free tier: 1,500 req/day).
Get your API key at: https://aistudio.google.com/app/apikey

Run: python phase1/3_embed_and_store.py
Output: data/chroma_db/
"""

import json
import os
import time
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBED_MODEL = "models/gemini-embedding-001"   # 768 dims, free tier
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "northwind_schema"
DOCS_PATH = "data/schema_docs.json"


def embed_texts(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """
    Embed texts in batches using Gemini gemini-embedding-001.

    task_type="retrieval_document" tells Gemini these are documents
    being indexed — use "retrieval_query" when embedding user questions
    at query time. This asymmetry improves retrieval accuracy.
    """
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = genai.embed_content(
            model=EMBED_MODEL,
            content=batch,
            task_type="retrieval_document",
        )
        # result["embedding"] is a list of vectors when input is a list
        all_embeddings.extend(result["embedding"])

        # Polite pause between batches to stay within rate limits
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """
    Embed a single user query at retrieval time.
    Uses task_type="retrieval_query" (different from document embedding).
    """
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


def main():
    print("=== Phase 1 / Step 3 (Gemini): Embedding & Storing in ChromaDB ===\n")

    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set in .env")
        print("Get your key at: https://aistudio.google.com/app/apikey")
        return

    genai.configure(api_key=GEMINI_API_KEY)

    # --- Load documents ---
    if not os.path.exists(DOCS_PATH):
        print(f"ERROR: {DOCS_PATH} not found. Run 2_document_schema.py first.")
        return

    with open(DOCS_PATH) as f:
        documents = json.load(f)

    print(f"1. Loaded {len(documents)} documents from {DOCS_PATH}")

    # --- Set up ChromaDB ---
    os.makedirs(CHROMA_PATH, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete existing collection so re-runs are idempotent
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        print(f"2. Cleared existing '{COLLECTION_NAME}' collection")
    except Exception:
        print(f"2. Creating new '{COLLECTION_NAME}' collection")

    # Gemini gemini-embedding-001 produces 768-dim vectors
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # --- Generate embeddings ---
    print(f"\n3. Generating embeddings with {EMBED_MODEL}...")
    texts = [doc["content"] for doc in documents]
    embeddings = embed_texts(texts)
    print(f"   Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")

    # --- Upsert into ChromaDB ---
    print("\n4. Storing in ChromaDB...")
    collection.upsert(
        ids=[doc["id"] for doc in documents],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "type": doc["type"],
                "table": doc.get("table", ""),
            }
            for doc in documents
        ],
    )
    print(f"   Stored {collection.count()} documents in '{COLLECTION_NAME}'")

    # --- Smoke test ---
    print("\n5. Smoke test — querying: 'total revenue by customer'")
    test_embedding = embed_query("total revenue by customer")

    results = collection.query(
        query_embeddings=[test_embedding],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    print("   Top 3 results:")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        similarity = 1 - dist
        print(f"\n   [{i+1}] type={meta['type']}  table={meta.get('table', '—')}  similarity={similarity:.3f}")
        print(f"       {doc[:120].strip()}...")

    print("\n✅ Phase 1 complete! Your vector store is ready.")
    print(f"   ChromaDB persisted at: {CHROMA_PATH}/")
    print("\n   What's next:")
    print("   → Phase 2: Build the query router + SQL + vector retrieval paths")
    print("      (uses Groq for LLM generation — free, very fast)")


if __name__ == "__main__":
    main()