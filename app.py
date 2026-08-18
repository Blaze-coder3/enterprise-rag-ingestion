import streamlit as st
import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
load_dotenv(override=True)

st.set_page_config(
    page_title="Enterprise RAG Ingestion Pipeline",
    page_icon="🧊",
    layout="wide",
)

# Apply custom dark theme styles with ultra-sleek sidebar design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Radial background gradient */
    .stApp {
        background: radial-gradient(circle at 50% 50%, rgb(15, 20, 35) 0%, rgb(8, 10, 18) 100%);
    }
    
    /* Sidebar glassmorphic container styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 12, 22, 0.98) 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5) !important;
    }
    
    /* Sidebar header & text formatting */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #F8FAFC !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stSidebar"] label {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        letter-spacing: 0.3px;
    }
    
    /* Sidebar Input fields & selectboxes styling */
    [data-testid="stSidebar"] div[data-baseweb="input"], 
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        color: #F8FAFC !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    [data-testid="stSidebar"] div[data-baseweb="input"]:focus-within, 
    [data-testid="stSidebar"] div[data-baseweb="select"]:focus-within {
        border-color: #6366F1 !important;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.35) !important;
    }

    /* Sidebar Navigation Links */
    [data-testid="stSidebarNav"] {
        padding-top: 10px;
    }
    [data-testid="stSidebarNav"] ul {
        gap: 8px;
    }
    [data-testid="stSidebarNav"] a {
        background-color: rgba(30, 41, 59, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 12px !important;
        color: #94A3B8 !important;
        padding: 10px 14px !important;
        font-size: 0.95rem !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(99, 102, 241, 0.12) !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
        color: #F8FAFC !important;
        transform: translateX(4px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.15) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.6) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.15) !important;
    }

    /* Sidebar buttons styling */
    [data-testid="stSidebar"] button {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3) !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stSidebar"] button:hover {
        box-shadow: 0 6px 18px rgba(124, 58, 237, 0.5) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Premium glassmorphic cards for metrics */
    div[data-testid="metric-container"] {
        background-color: rgba(30, 41, 59, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(12px);
    }
    
    /* Hover micro-animation for cards */
    div[data-testid="metric-container"]:hover {
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 10px 20px -3px rgba(99, 102, 241, 0.15);
        transform: translateY(-2px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Pulsing status indicators */
    @keyframes pulse-glow {
        0% { box-shadow: 0 0 0 0 var(--pulse-color); }
        70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
    }
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse-glow 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

import httpx

def check_backend_status():
    status = {"api": False, "qdrant": False, "llm": "Offline", "llm_color": "#EF4444"}
    
    # 1. API Status
    try:
        r = httpx.get("http://127.0.0.1:8000/v1/health", timeout=1.0)
        if r.status_code < 400:
            status["api"] = True
    except Exception:
        pass

    # 2. Qdrant Status
    try:
        r = httpx.get("http://127.0.0.1:6333/", timeout=1.0)
        if r.status_code == 200:
            status["qdrant"] = True
    except Exception:
        pass

    # 3. LLM Status
    llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if llm_provider == "mock":
        status["llm"] = "Mock Mode Active"
        status["llm_color"] = "#F59E0B"
    elif llm_provider == "openai":
        if os.getenv("OPENAI_API_KEY"):
            status["llm"] = "OpenAI Cloud Active"
            status["llm_color"] = "#10B981"
        else:
            status["llm"] = "OpenAI (Key Missing)"
    elif llm_provider == "gemini":
        if os.getenv("GEMINI_API_KEY"):
            status["llm"] = "Gemini Cloud Active"
            status["llm_color"] = "#10B981"
        else:
            status["llm"] = "Gemini (Key Missing)"
    elif llm_provider == "ollama":
        try:
            r = httpx.get("http://127.0.0.1:11434/", timeout=1.0)
            if r.status_code == 200:
                status["llm"] = f"Ollama ({os.getenv('LLM_MODEL', 'phi3')})"
                status["llm_color"] = "#10B981"
        except Exception:
            status["llm"] = "Ollama Offline"
    elif llm_provider == "groq":
        if os.getenv("GROQ_API_KEY"):
            status["llm"] = f"Groq ({os.getenv('LLM_MODEL', 'groq/compound-mini')})"
            status["llm_color"] = "#10B981"
        else:
            status["llm"] = "Groq (Key Missing)"
            
    return status

system_health = check_backend_status()

# Sidebar Header Branding & Status
with st.sidebar:
    status_text = "System Active" if system_health["api"] else "Backend Offline"
    status_color = "#10B981" if system_health["api"] else "#EF4444"
    st.markdown(f"""
    <div style="padding: 10px 0 20px 0; text-align: center;">
        <div style="background: linear-gradient(135deg, #6366F1, #8B5CF6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 1.4rem; font-weight: 800;">
            ⚡ Enterprise RAG
        </div>
        <div style="font-size: 0.78rem; color: {status_color}; font-weight: 600; margin-top: 4px; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span class="status-dot" style="background-color: {status_color}; --pulse-color: {status_color}80;"></span> {status_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Layout: Title & Hero
st.markdown("<h1 style='text-align: center; font-weight: 800; color: #F8FAFC;'>🧊 Enterprise RAG Ingestion Pipeline</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.15rem; margin-bottom: 2rem;'>Scalable, asynchronous document ingestion with tenant isolation & hybrid vector search.</p>", unsafe_allow_html=True)

# Load Operational Statistics from local SQLite
DB_PATH = "./data/pipeline.db"
total_docs = 0
active_tenants = 0
ready_docs = 0
success_rate = "100%"

if os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        df_docs = pd.read_sql_query("SELECT * FROM documents", conn)
        total_docs = len(df_docs)
        
        df_tenants = pd.read_sql_query("SELECT * FROM tenants", conn)
        active_tenants = len(df_tenants)
        
        ready_docs = len(df_docs[df_docs['status'] == 'ready'])
        
        if total_docs > 0:
            success_rate = f"{(ready_docs / total_docs) * 100:.1f}%"
        conn.close()
    except Exception:
        pass

# Dashboard Column Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric(label="Ingested Documents", value=total_docs)
col2.metric(label="Active Tenants", value=active_tenants)
col3.metric(label="Successfully Indexed", value=ready_docs)
col4.metric(label="Pipeline Success Rate", value=success_rate)

st.divider()

# Visual Info Cards
st.markdown("### 🛠️ Architecture & Multi-Tenancy Design")
col_arch1, col_arch2 = st.columns(2)

with col_arch1:
    st.info("""
    **🚀 Asynchronous Ingestion & Concurrency Limiting**
    * Documents uploaded to `/v1/ingest` are parsed out-of-process (offloaded to threadpools using `asyncio.to_thread`) to prevent blocking the event loop.
    * A per-tenant concurrent semaphore guarantees fairness and limits resource exhaustion from "noisy neighbor" uploads.
    * Integrates **IBM Docling** as primary layout-preserving parser with automatic fallback to **Azure Document Intelligence** if text density limits fail.
    """)

with col_arch2:
    st.info("""
    **🔒 Strict Tenant isolation & Access Control Lists**
    * Multi-tenancy is enforced down to the Vector DB layer via Qdrant payload filtering on `tenant_id` and `access_groups`.
    * Combines dense embeddings (FastEmbed `all-MiniLM-L6-v2`) and sparse indices (BM25) fused via Reciprocal Rank Fusion (RRF).
    * Passed through a local Cross-Encoder reranker prior to context injection to maximize retrieval precision.
    """)

# System Design Section
st.markdown("### 🏛️ Pipeline State Machine Architecture")
st.markdown("""
Every uploaded document transitions through an auditable sequence tracked dynamically in SQLite:
1. **RECEIVED**: Document bits arrive.
2. **STORED**: Safe backup in blob storage.
3. **QUEUED**: Ingestion task queued.
4. **PARSING**: IBM Docling or Azure Document Intelligence extraction.
5. **QUALITY_CHECK**: Layout validation gate.
6. **NORMALIZED**: Standardized to Canonical Document.
7. **CHUNKING**: Semantic chunking by block structure.
8. **EMBEDDING**: Dense & Sparse representations generated.
9. **INDEXING**: Uploaded to Qdrant vector store.
10. **READY**: Active and searchable.
""")

with st.sidebar:
    st.divider()
    api_color = "#10B981" if system_health["api"] else "#EF4444"
    api_txt = "Online (8000)" if system_health["api"] else "Offline"
    
    qdrant_color = "#10B981" if system_health["qdrant"] else "#EF4444"
    qdrant_txt = "Online (6333)" if system_health["qdrant"] else "Offline"
    
    llm_color = system_health["llm_color"]
    llm_txt = system_health["llm"]
    
    st.markdown(f"""
    <div style="font-size: 0.8rem; color: #94A3B8; background: rgba(15, 23, 42, 0.4); padding: 14px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.06); backdrop-filter: blur(8px);">
        <div style="margin-bottom: 8px; font-weight: bold; color: #F8FAFC; letter-spacing: 0.5px; font-size: 0.75rem; text-transform: uppercase;">Service Registry Status</div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-size: 0.85rem;">Backend API</span>
            <div style="display: flex; align-items: center;">
                <span class="status-dot" style="background-color: {api_color}; --pulse-color: {api_color}80; margin-right: 6px; width: 6px; height: 6px;"></span>
                <span style="font-size: 0.8rem; color: {api_color}; font-weight: 600;">{api_txt}</span>
            </div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-size: 0.85rem;">Vector DB</span>
            <div style="display: flex; align-items: center;">
                <span class="status-dot" style="background-color: {qdrant_color}; --pulse-color: {qdrant_color}80; margin-right: 6px; width: 6px; height: 6px;"></span>
                <span style="font-size: 0.8rem; color: {qdrant_color}; font-weight: 600;">{qdrant_txt}</span>
            </div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-size: 0.85rem;">LLM Engine</span>
            <div style="display: flex; align-items: center;">
                <span class="status-dot" style="background-color: {llm_color}; --pulse-color: {llm_color}80; margin-right: 6px; width: 6px; height: 6px;"></span>
                <span style="font-size: 0.8rem; color: {llm_color}; font-weight: 600;">{llm_txt}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

