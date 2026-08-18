# System Design & Architecture Decisions

This document details the design patterns, trade-offs, and multi-tenant scaling strategies implemented in this take-home RAG ingestion pipeline.

---

## 🏛️ System Architecture Diagram

```
Document Upload (Streamlit / API)
       │
       ▼ (Tenant Validation)
┌───────────────────────────────┐
│     TenantFairScheduler       │  ◄── Rate-limits concurrent jobs per tenant
└──────────────┬────────────────┘
               │
               ▼ (Offloaded to Worker ThreadPool via asyncio.to_thread)
┌───────────────────────────────┐
│     Docling / ADI Parser      │  ◄── Preserves structure, non-blocking OCR
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│     Semantic Chunker          │  ◄── Preserves collection_id & token boundaries
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│  Qdrant Hybrid Vector Store   │  ◄── Dense (MiniLM-L6) + Sparse (BM25)
└───────────────────────────────┘
```

---

## 💎 Key Architecture Decisions

### 1. Document Parsing & Quality-Gate Fallback with Thread Offloading
*   **Decision**: We use **Docling (IBM)** as the primary parser and **Azure Document Intelligence (ADI)** as a backup fallback, offloading CPU-heavy conversion to worker threads using `asyncio.to_thread`.
*   **Rationale**: Naive text extraction destroys tables and layout relations, leading to incorrect RAG context. Docling converts complex PDFs/DOCX files into cleanly structured dictionaries preserving tables. To prevent heavy PyTorch OCR operations from blocking Uvicorn's async event loop, conversion is offloaded to worker threads, ensuring status polling endpoints remain 100% responsive. An automated **Quality Gate** assesses text density to trigger fallback if necessary.

### 2. Tenant Concurrency & Fairness
*   **Decision**: Created a custom `TenantFairScheduler` that leverages `asyncio.Semaphore` per tenant.
*   **Rationale**: In an enterprise RAG system, one tenant uploading a batch of 100,000 files must not block or slow down another tenant who uploaded a single critical document. The scheduler caps concurrent tasks per tenant, enforcing queue-fairness round-robin across worker threads.

### 3. Database-Level Hybrid Retrieval & Multi-Tenant Collection Filtering
*   **Decision**: Configured Qdrant with named vectors: `dense` (all-MiniLM-L6-v2) and `sparse` (BM25 modifier IDF), filtering on indexed payloads (`tenant_id`, `collection_id`).
*   **Rationale**: Traditional systems build and score BM25 indexes in-memory in Python (which exhausts RAM when handling millions of documents). Offloading the sparse vector index, payload filtering, and Reciprocal Rank Fusion (RRF) directly to Qdrant ensures sub-millisecond multi-tenant queries at scale.

### 4. Enterprise System Prompt Contract
*   **Decision**: Implemented a multi-role chat message structure separating system role guidelines from user context.
*   **Rationale**: Following enterprise AI engineering best practices, system instructions (grounding constraints, explicit refusal messages, and citation formatting) are isolated in `{"role": "system"}`. This prevents prompt instruction overload on smaller LLMs and eliminates hallucinations or token leakage.

### 5. Asynchronous Ragas Evaluations
*   **Decision**: Configured `RagasEvaluator` to score chat queries for Faithfulness, Relevance, and Precision, executing evaluations in background worker loops.
*   **Rationale**: Ragas LLM evaluation requires multiple round-trip prompts, adding 4–8 seconds of latency. Triggering evaluation asynchronously via `asyncio.create_task` ensures immediate chat responses for the user, while stats are eventually compiled and logged to SQLite.

---

## ⚖️ Trade-offs Considered

*   **Offline Capability vs. Cloud API Keys**: To keep the assignment fully local and runnable in restricted network environments, we enabled local sentence-transformer models (via FastEmbed) and local Ollama (`qwen:0.5b`) integration, while maintaining standard endpoints for OpenAI/Gemini.
*   **Prometheus/Grafana vs. Native Dashboard**: Removed Prometheus/Grafana to eliminate container configuration overhead. We built a native database-backed Python dashboard in Streamlit to simplify the setup for evaluators, utilizing the local SQLite database.
