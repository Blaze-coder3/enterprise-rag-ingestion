# Enterprise RAG Ingestion Pipeline

A production-grade, multi-tenant document ingestion pipeline for Retrieval-Augmented Generation (RAG) applications.

This system is designed to handle **millions of documents** from **hundreds of tenants** while ensuring resource fairness, schema normalization, hybrid search retrieval, and grounded conversational generation.

---

## 🚀 Key Features

*   **Thread-Offloaded Docling Document Parser**: Parses PDFs, Word files, HTML, and images into structured content preserving tables and layout. CPU-heavy PyTorch parsing is offloaded to background worker threads (`asyncio.to_thread`) to maintain 100% async API responsiveness.
*   **Dual Vector Hybrid Search**: Synthesizes dense semantic embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and sparse keyword indexes (`BM25`) directly in **Qdrant** with strict multi-tenant payload isolation (`tenant_id`, `collection_id`).
*   **Tenant Concurrency Fairness**: An active fair scheduler (`TenantFairScheduler`) limits concurrent jobs per tenant using `asyncio.Semaphore` to prevent resource starvation.
*   **Enterprise Multi-Role Prompt Contract**: Implements isolated system-role instructions based on top AI engineering standards (strict context grounding, explicit refusal strings, and in-line `[Source: <doc_id>, p.<page_num>]` citations).
*   **Local LLM Chat Grounding**: Grounded question-answering with citation tracking powered by local **Ollama** (`qwen:0.5b` or other model configs) as well as OpenAI / Gemini endpoints.
*   **RAGAS Evaluation & Monitor Dashboard**: A native Streamlit monitor page displaying real-time database-backed stats on ingestion stage latencies and Ragas LLM evaluations (Faithfulness, Answer Relevance, Context Precision).
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
Pull and run the lightweight `qwen:0.5b` model:
```powershell
ollama run qwen:0.5b
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
LLM_MODEL=qwen:0.5b
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

To run the unit tests verifying the chunker, parser adapters, and fair scheduler:
```powershell
python -m pytest
```

---

## 🎬 Demo

<video src="demo.mp4" controls width="100%"></video>

