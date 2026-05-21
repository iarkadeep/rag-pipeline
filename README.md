# Northwind Analytics — RAG-Powered Analytics Chatbot

A production-style chatbot that answers plain-English questions about a sales database using a Retrieval-Augmented Generation (RAG) pipeline. Combines semantic vector search with SQL generation to deliver accurate, explainable answers over structured business data.

---

## Demo

Ask questions like:
- *"Who are the top 5 customers by revenue?"*
- *"What is total revenue for 1997?"*
- *"Which product category generates the most sales?"*
- *"What does AOV mean and what is ours?"*

The app classifies each question, retrieves relevant schema context, generates SQL, executes it against a live database, and returns a plain-English answer — all in under 2 seconds.

---

## Architecture

```
User question
      │
      ▼
Query Router          ← Gemini 1.5 Flash classifies: sql / vector / both
      │
      ▼
Vector Retrieval      ← Gemini Embedding embeds query → ChromaDB similarity search
      │                  returns relevant schema docs as context
      ▼
SQL Generation        ← Gemini 1.5 Flash writes SQL using schema context
      │
      ▼
SQL Execution         ← SQLAlchemy runs query against PostgreSQL (Northwind)
      │
      ▼
Answer Generation     ← Gemini 1.5 Flash formats results into plain English
      │
      ▼
Streamlit UI          ← displays answer, route badge, SQL expander, raw results
```

Every query makes 3 Gemini API calls (router + SQL gen + answer gen) plus 1 embedding call — all on the free tier.

---

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| LLM (routing, SQL gen, answer gen) | Gemini 1.5 Flash |
| Embeddings | Gemini Embedding 001 |
| Vector store | ChromaDB (local persistent) |
| SQL database | PostgreSQL 15 (Docker) |
| ORM | SQLAlchemy |
| Dataset | Northwind (10 tables, ~2,000 rows) |

---

## Project Structure

```
rag-analytics-chatbot/
├── app.py                        # Streamlit entry point
├── components.py                 # UI rendering helpers
├── config.py                     # Centralised settings and model config
├── requirements.txt              # Pinned dependencies
├── .env                          # API keys and DB URL (not committed)
│
├── phase1/                       # Data foundation scripts
│   ├── 1_load_db.py              # Load Northwind into PostgreSQL
│   ├── 2_document_schema.py      # Generate plain-English schema docs
│   └── 3_embed_and_store.py      # Embed docs and store in ChromaDB
│
├── phase2/                       # Retrieval pipeline
│   ├── query_router.py           # Classifies query as sql / vector / both
│   ├── sql_chain.py              # Generates and executes SQL
│   ├── vector_retrieval.py       # Embeds query and searches ChromaDB
│   └── pipeline.py              # Wires all components into ask()
│
└── data/
    ├── chroma_db/                # Persisted ChromaDB vector store
    └── schema_docs.json          # Generated schema documentation
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker (for PostgreSQL)
- A [Google AI Studio](https://aistudio.google.com/app/apikey) account (free Gemini API key)

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/rag-analytics-chatbot.git
cd rag-analytics-chatbot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your-gemini-api-key-here
DB_URL=postgresql://your_user:your_password@localhost:5432/northwind
```

### 5. Start PostgreSQL and load the database

```bash
# Pull and run PostgreSQL in Docker
docker run --name northwind-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=northwind \
  -p 5432:5432 \
  -d postgres:15

# Download the Northwind SQL file
curl -o data/northwind.sql https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql

# Load data into PostgreSQL
docker exec -i northwind-pg psql -U postgres -d northwind < data/northwind.sql
```

### 6. Run the Phase 1 setup scripts

These only need to be run once to set up the vector store.

```bash
python phase1/2_document_schema.py
python phase1/3_embed_and_store.py
```

### 7. Launch the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## How It Works

### Query routing
Each user question is classified into one of three routes:

- `sql` — questions needing structured data (counts, totals, rankings)
- `vector` — questions needing definitions or business term explanations
- `both` — questions needing a database query and contextual explanation

### Retrieval-Augmented SQL Generation
Rather than hardcoding the database schema into a prompt, schema descriptions are stored as embeddings in ChromaDB. At query time, the most relevant table descriptions, column definitions, and example queries are retrieved and injected into the SQL generation prompt dynamically. This means schema updates automatically improve query quality without changing any code.

### Why this matters
Most text-to-SQL systems fail on domain-specific schemas because the LLM doesn't understand business-specific column meanings (e.g. that `discount` is a fraction, not a percentage). The vector retrieval step solves this by grounding every SQL generation call in hand-written schema documentation.

---

## Key Design Decisions

**Asymmetric embeddings** — Documents are embedded with `task_type="retrieval_document"` and queries with `task_type="retrieval_query"`. Gemini's embedding model is trained asymmetrically, which improves retrieval accuracy compared to using the same task type for both.

**Schema documentation as the knowledge base** — The quality of the RAG system is directly proportional to the quality of the schema documentation in `phase1/2_document_schema.py`. Rich table descriptions, business glossary entries, and example Q&A pairs act as the system's domain knowledge.

**SQL validation layer** — The LLM generates SQL but never executes it directly. All queries pass through SQLAlchemy, which handles connection pooling, parameterisation, and error catching before results reach the user.

**Separation of retrieval and generation** — The pipeline separates schema retrieval (ChromaDB) from answer generation (Gemini). This makes each component independently testable and swappable.

---

## Production Upgrade Path

This project is built as a working prototype. For production scale:

| Component | Current | Production upgrade |
|---|---|---|
| Vector store | ChromaDB (local files) | Pinecone, Weaviate, or pgvector on RDS |
| SQL database | PostgreSQL in Docker | AWS RDS or Google Cloud SQL |
| API | Streamlit | FastAPI + Docker + Kubernetes |
| Secrets | `.env` file | AWS Secrets Manager or HashiCorp Vault |
| Observability | None | LangSmith for query tracing |
| Embeddings pipeline | Run once manually | Nightly scheduled job for data freshness |

---

## License

MIT