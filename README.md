# Enterprise RAG Ingestion Pipeline

A production-grade, multi-tenant document ingestion pipeline for Retrieval-Augmented Generation (RAG) applications.

This system is designed to handle **millions of documents** from **hundreds of tenants** while ensuring resource fairness, schema normalization, hybrid search retrieval, and grounded conversational generation.
---

## 📺 Walkthrough Demo

A video demonstration showcasing the multi-tenant document ingestion pipeline, real-time stage timeline tracking, ingestion history portals, and Groq-grounded conversational search is available here:
🎥 **[Play Walkthrough Demo (demo1.mp4)](demo1.mp4)**

---

## 🚀 Key Features

*   **Multi-Format Document Ingestion Router**: Branches files dynamically based on extension. Integrates a native spreadsheet parser (**Pandas + OpenPyXL**) for data tables, a BeautifulSoup (**BS4**) parser for HTML documents, and IBM's **Docling** for complex PDFs/Word files.
*   **Defensive QA Gatekeeper**: Evaluates text density to detect bad OCR or empty extractions, dynamically marking documents that fail metrics as `NEEDS_REVIEW` and appending `low_confidence_extraction` tags instead of allowing raw corrupted vectors to pollute the index.
*   **Object Storage Integration**: Raw documents are saved durably to local Blob Storage immediately upon receipt to guarantee disaster recovery and reprocessing capabilities.
*   **Dual Vector Hybrid Search**: Synthesizes dense semantic embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and sparse keyword indexes (`BM25`) directly in **Qdrant** with strict multi-tenant payload isolation (`tenant_id`, `collection_id`).
*   **Cross-Encoder Reranking & ACL Security**: Initial retrieval of top 50 chunks is re-scored by a `sentence-transformers` CrossEncoder down to top 5, while Qdrant enforces payload filtering against the user's `access_groups` (RBAC).
*   **Data Integrity & Sticky-Row Injection**: Prevents tabular insurance data structure loss. During chunking, headers are dynamically prepended to data row contexts (e.g. `Header1: Value1, Header2: Value2`), preserving multi-column relationships.
*   **Tenant Concurrency Fairness**: Per-tenant concurrency limits via `asyncio.Semaphore` prevent a single tenant from exhausting local resources (true round-robin scheduling is delegated to the production queueing layer).
*   **Hostile-Witness Prompt & Legal Disclaimers**: Implements a prompt-tuned expert Legal and Medical Assessor persona. Answers are strictly grounded, and the model outputs `"UNABLE TO VERIFY"` if the context is insufficient. Prompts automatically inject legal disclaimers when parsing unverified structures.
*   **Local LLM Chat Grounding**: Grounded question-answering with citation tracking powered by local **Ollama** (`llama3.2:1b` or other model configs) as well as OpenAI / Gemini endpoints.
*   **Asynchronous RAGAS Evaluation**: Executes the asynchronous evaluation loop of RAGAS metrics (**Faithfulness**, **Context Precision**, and **Answer Relevancy**) using an isolated background task, decoupled from the core application thread via lazy-loading imports.
*   **Ultra-Sleek Glassmorphic UI**: High-end Streamlit dashboard with custom CSS, dark radial gradients, responsive stage timelines, and real-time workspace context switching.
*   **Jaeger Distributed Tracing**: Complete OpenTelemetry span logging to track document ingestion and chat traces.

---

## 🛠️ Setup & Execution

### Prerequisites
*   [Python 3.10+](https://www.python.org/downloads/)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (to run Qdrant and Jaeger)
*   [Ollama](https://ollama.com/) (to run local LLM generation)

### 1. Start Infrastructure
Run the following command to start Qdrant and Jaeger:
```powershell
docker compose up -d
```
*   **Qdrant UI**: http://localhost:6333/dashboard
*   **Jaeger Traces**: http://localhost:16686

### 2. Configure Local LLM (Ollama)
Pull and run the lightweight `llama3.2:1b` model:
```powershell
ollama run llama3.2:1b
```

### 3. Install Dependencies
Create your virtual environment, activate it, and install package dependencies:
```powershell
python -m venv .venv
.venv\Scripts\activate
uv pip install -e .[test]
```

### 4. Configure Environment
Create a `.env` file in the root directory (matching `.env.example`):
```env
PORT=8000
ENVIRONMENT=development
LOG_LEVEL=info

QDRANT_URL=http://localhost:6333
DATABASE_URL=sqlite:///data/pipeline.db
BLOB_STORAGE_PATH=./data/blobs

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
SPARSE_EMBEDDING_MODEL=Qdrant/bm25

JAEGER_ENDPOINT=localhost:4317

LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:1b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

### 5. Start Backend API
```powershell
uvicorn src.rag_pipeline.main:app --host 0.0.0.0 --port 8000 --reload
```
*   **Interactive API Docs**: http://localhost:8000/docs

### 6. Start Dashboard UI
```powershell
streamlit run app.py
```
*   **Dashboard UI**: http://localhost:8501

---

## 🧪 Testing

To run the offline isolated unit test suite verifying format routing, the QA gatekeeper, sticky row injection, and database multi-tenant filters:
```powershell
python -m pytest -v tests/
```
The test suite utilizes mocks for all external connections (Qdrant, embedding models, LLMs) to run deterministically in under 2 seconds.

---

## 🎬 Demo

Watch the full demonstration of the pipeline in action:

[**👉 Click here to watch or download the demo video (`demo1.mp4`)**](https://github.com/Blaze-coder3/enterprise-rag-ingestion/raw/main/demo1.mp4)

*(Note: Because the video is a high-quality 65MB file, GitHub's inline viewer may not preview it directly on the repository page. Clicking the link will allow you to stream or download the raw file.)*
