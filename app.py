import streamlit as st
import os
import sqlite3
import pandas as pd

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
        gap: 6px;
    }
    [data-testid="stSidebarNav"] a {
        background-color: rgba(30, 41, 59, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        color: #94A3B8 !important;
        padding: 8px 12px !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(99, 102, 241, 0.15) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        color: #F8FAFC !important;
        transform: translateX(4px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.25) 0%, rgba(139, 92, 246, 0.2) 100%) !important;
        border: 1px solid #6366F1 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25) !important;
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
</style>
""", unsafe_allow_html=True)

# Sidebar Header Branding & Status
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 20px 0; text-align: center;">
        <div style="background: linear-gradient(135deg, #6366F1, #8B5CF6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 1.4rem; font-weight: 800;">
            ⚡ Enterprise RAG
        </div>
        <div style="font-size: 0.78rem; color: #10B981; font-weight: 600; margin-top: 4px; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span style="height: 8px; width: 8px; background-color: #10B981; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #10B981;"></span> System Active
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
st.markdown("### 🛠️ Architecture Overview")
col_arch1, col_arch2 = st.columns(2)

with col_arch1:
    st.info("""
    **🚀 Asynchronous Ingestion Worker Pool**
    * Documents uploaded to the `/v1/ingest` API endpoint are immediately queued and processed in the background using an asynchronous Python worker pool (`WorkerPool`).
    * Implements tenant-level **Fair Scheduling** to prevent resource starvation.
    """)

with col_arch2:
    st.info("""
    **🔍 Dual Vector Hybrid Search**
    * Leverages Qdrant to perform both dense embedding retrieval (using local `sentence-transformers`) and sparse keyword retrieval (using BM25).
    * Performs reciprocal rank fusion (RRF) to combine results for maximum search accuracy.
    """)

with st.sidebar:
    st.divider()
    st.markdown("""
    <div style="font-size: 0.75rem; color: #64748B; background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05);">
        <div>🟢 <b>Backend API:</b> Online (8000)</div>
        <div style="margin-top: 4px;">🟢 <b>Vector DB:</b> Qdrant Hybrid</div>
        <div style="margin-top: 4px;">🟢 <b>LLM Engine:</b> Ollama (Qwen)</div>
    </div>
    """, unsafe_allow_html=True)
