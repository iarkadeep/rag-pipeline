# Northwind Analytics — RAG-Powered Analytics Chatbot

A production-style chatbot that answers plain-English questions about a sales database using a Retrieval-Augmented Generation (RAG) pipeline. Combines semantic vector search with SQL generation to deliver accurate, explainable answers over structured business data.
(NOTE: - Use Python 3.10 specifically (3.11+ may cause dependency issues))
**Live demo:** [northwind.streamlit.app](https://northwind.streamlit.app)

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
Query Router          ← Groq (Llama 3.1 70B) classifies: sql / vector / both
      │
      ▼
Vector Retrieval      ← Gemini Embedding embeds query → ChromaDB similarity search
      │                  returns relevant schema docs as context
      ▼
SQL Generation        ← Groq (Llama 3.3 70B) writes SQL using schema context
      │
      ▼
SQL Execution         ← SQLAlchemy runs query against Neon PostgreSQL
      │
      ▼
Answer Generation     ← Groq (Llama 3.3 70B) formats results into plain English
      │
      ▼
Streamlit UI          ← displays answer, route badge, SQL expander, raw results
```

Every query makes 3 Groq API calls (router + SQL gen + answer gen) plus 1 Gemini embedding call — all on free tiers.

---

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit Community Cloud |
| LLM (routing, SQL gen, answer gen) | Groq (Llama 3.1 70B) |
| Embeddings | Gemini Embedding 001 |
| Vector store | ChromaDB (committed to repo) |
| SQL database | Neon (free managed PostgreSQL) |
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
- A [Google AI Studio](https://aistudio.google.com/app/apikey) account (free Gemini API key)
- A [Groq](https://console.groq.com) account (free API key)
- A [Neon](https://neon.tech) account (free managed PostgreSQL)

### 1. Clone the repo

```bash
git clone https://github.com/iarkadeep/rag-analytics-chatbot.git
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
GROQ_API_KEY=your-groq-api-key-here
DB_URL=your-neon-connection-string-here
```

### 5. Set up Neon and load the database

1. Go to [neon.tech](https://neon.tech) and create a free project
2. Copy your connection string from the Neon dashboard
3. Download and load the Northwind dataset:

```bash
# Download Northwind SQL file
curl -o data/northwind.sql https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql

# Load into Neon (via Docker if psql not installed locally)
docker run --rm -i postgres:15 psql your-neon-connection-string < data/northwind.sql
```

### 6. Run the Phase 1 setup scripts

These only need to be run once to build the vector store.

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

## Deployment

This app is deployed on **Streamlit Community Cloud** with **Neon** as the managed PostgreSQL backend — both free forever.

### Deploy your own instance

1. Push this repo to GitHub (make sure `data/chroma_db/` is committed and `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your repo → set main file to `app.py`
4. Click **Advanced settings** → **Secrets** and add:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
GROQ_API_KEY = "your-groq-api-key"
DB_URL = "your-neon-connection-string"
```

5. Click **Deploy**

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

**Separation of retrieval and generation** — The pipeline separates schema retrieval (ChromaDB) from answer generation (Groq). This makes each component independently testable and swappable.

---

## Production Upgrade Path

This project is built as a working prototype. For production scale:

| Component | Current | Production upgrade |
|---|---|---|
| Vector store | ChromaDB (in repo) | Pinecone, Weaviate, or pgvector on RDS |
| SQL database | Neon free tier | AWS RDS or Google Cloud SQL |
| API | Streamlit | FastAPI + Docker + Kubernetes |
| Secrets | Streamlit secrets | AWS Secrets Manager or HashiCorp Vault |
| Observability | None | LangSmith for query tracing |
| Embeddings pipeline | Run once manually | Nightly scheduled job for data freshness |

---

## License

MIT