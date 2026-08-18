import streamlit as st
import httpx
import time
import os
from dotenv import load_dotenv
load_dotenv(override=True)

st.set_page_config(page_title="Ingest Documents", page_icon="📄", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    .stApp {
        background: radial-gradient(circle at 50% 50%, rgb(15, 20, 35) 0%, rgb(8, 10, 18) 100%);
    }
    /* Sidebar glassmorphic container styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 12, 22, 0.98) 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5) !important;
    }
    [data-testid="stSidebar"] label {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stSidebarNav"] a {
        background-color: rgba(30, 41, 59, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 12px !important;
        color: #94A3B8 !important;
        margin-bottom: 4px !important;
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
    
    /* Drag & Drop File Uploader custom premium styling */
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.2) !important;
        border: 2px dashed rgba(99, 102, 241, 0.3) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        aspect-ratio: 1 / 1 !important; /* Enforces a perfect square shape */
        min-height: 280px !important;
        width: 100% !important;
        max-width: 320px !important; /* Cap maximum width to look balanced */
        margin: 0 !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(99, 102, 241, 0.7) !important;
        background: rgba(99, 102, 241, 0.06) !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.08) !important;
    }
    [data-testid="stFileUploader"] section {
        padding: 0 !important;
        background: transparent !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
    }
</style>
""", unsafe_allow_html=True)

def check_backend_status():
    status = {"api": False, "qdrant": False, "llm": "Offline", "llm_color": "#EF4444"}
    try:
        r = httpx.get("http://127.0.0.1:8000/v1/health", timeout=1.0)
        if r.status_code < 400:
            status["api"] = True
    except Exception:
        pass
    try:
        r = httpx.get("http://127.0.0.1:6333/", timeout=1.0)
        if r.status_code == 200:
            status["qdrant"] = True
    except Exception:
        pass
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

st.title("📄 Document Ingestion Pipeline")
st.markdown("Upload documents to your tenant's isolated storage and monitor their stage-by-step processing.")

import sqlite3
import pandas as pd

API_URL = os.getenv("API_URL", "http://localhost:8000")
DB_PATH = "./data/pipeline.db"

def get_active_tenants_and_collections():
    tenants = []
    tenant_collections_map = {}
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            try:
                df_t = pd.read_sql_query("SELECT tenant_id FROM tenants", conn)
                for t in df_t["tenant_id"].unique():
                    if t and t not in tenants:
                        tenants.append(t)
                        tenant_collections_map[t] = ["default"]
            except Exception:
                pass
                
            try:
                df_docs = pd.read_sql_query("SELECT DISTINCT tenant_id, collection_id FROM documents", conn)
                for _, row in df_docs.iterrows():
                    t = row["tenant_id"]
                    c = row["collection_id"]
                    if t:
                        if t not in tenants:
                            tenants.append(t)
                        if t not in tenant_collections_map:
                            tenant_collections_map[t] = []
                        if c and c not in tenant_collections_map[t]:
                            tenant_collections_map[t].append(c)
            except Exception:
                pass
            conn.close()
        except Exception:
            pass
            
    for t in tenants:
        if t not in tenant_collections_map or not tenant_collections_map[t]:
            tenant_collections_map[t] = ["default"]
            
    return tenants, tenant_collections_map

tenants_list, tenant_collections_map = get_active_tenants_and_collections()

# Input forms
import json

col_tenant, col_portal = st.columns([1, 1])

with col_tenant:
    st.markdown("### 🔑 Tenant & Context")
    selected_t = st.selectbox("Select Active Tenant", options=tenants_list + ["+ Enter Custom Tenant"])
    if selected_t == "+ Enter Custom Tenant":
        tenant_id = st.text_input("Tenant ID", value="tenant-acme")
        avail_collections = ["default", "001", "002"]
    else:
        tenant_id = selected_t
        avail_collections = tenant_collections_map.get(tenant_id, ["default", "001", "002"])
        if "default" not in avail_collections:
            avail_collections.insert(0, "default")
        
    selected_c = st.selectbox("Select Collection ID", options=avail_collections + ["+ Enter Custom Collection"])
    if selected_c == "+ Enter Custom Collection":
        collection_id = st.text_input("Collection ID", value="default")
    else:
        collection_id = selected_c
        
    document_type = st.selectbox("Document Type", ["contract", "manual", "financial", "other"])

with col_portal:
    st.markdown("### 📤 Ingestion Portal")
    uploaded_file = st.file_uploader("Choose a file (PDF, DOCX, TXT, HTML)", type=["pdf", "docx", "txt", "html"])

st.markdown("---")

# Collapsible advanced settings expander spanning full-width
with st.expander("⚙️ Advanced Pipeline Parameters (Optional Override)", expanded=False):
    col_adv1, col_adv2 = st.columns(2)
    
    with col_adv1:
        st.markdown("##### Parser Routing Settings")
        primary_parser = st.radio("Primary Parser Selection", ["IBM Docling", "Azure Doc Intelligence"], index=0)
        density_threshold = st.slider("Quality Gate Text Density Fallback", min_value=0.0, max_value=1.0, value=0.45, step=0.05,
                                      help="Trigger fallback parser if characters/pixels density is below this threshold.")
        
    with col_adv2:
        st.markdown("##### Semantic Chunking & Indexing")
        chunk_size = st.slider("Semantic Chunk Size (Tokens)", min_value=128, max_value=1024, value=512, step=64)
        chunk_overlap = st.slider("Chunk Overlap (Tokens)", min_value=0, max_value=256, value=64, step=16)
        embedders = st.multiselect("Vector Embedding Indexing", ["Dense Embeddings", "Sparse (BM25) Embeddings"], default=["Dense Embeddings", "Sparse (BM25) Embeddings"])

if uploaded_file is not None:
    if st.button("Start Ingestion Pipeline 🚀", use_container_width=True):
        with st.spinner("Uploading document to backend..."):
            try:
                # Prepare payload with layout override variables in metadata
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

                
                meta_dict = {
                    "primary_parser": "docling" if "Docling" in primary_parser else "azure",
                    "quality_gate_threshold": density_threshold,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "indexing_modes": [e.split()[0].lower() for e in embedders]
                }
                
                data = {
                    "tenant_id": tenant_id,
                    "collection_id": collection_id,
                    "document_type": document_type,
                    "metadata": json.dumps(meta_dict)
                }
                
                # Post to backend
                response = httpx.post(f"{API_URL}/v1/ingest", data=data, files=files, timeout=30.0)
                
                if response.status_code == 202:
                    ingest_data = response.json()
                    st.success(f"File uploaded successfully! Job ID: {ingest_data['job_id']}")
                    
                    # Store job info in session state for timeline tracking
                    st.session_state["active_job"] = {
                        "job_id": ingest_data["job_id"],
                        "document_id": ingest_data["document_id"],
                        "tenant_id": tenant_id,
                        "filename": uploaded_file.name
                    }
                else:
                    st.error(f"Upload failed: {response.text}")
            except Exception as e:
                st.error(f"Error connecting to backend API: {str(e)}")

# Display active pipeline timeline
if "active_job" in st.session_state:
    job = st.session_state["active_job"]
    st.divider()
    st.subheader(f"Pipeline Ingestion Timeline: {job['filename']}")
    
    # Progress stages
    stages = [
        ("received", "📥 Received"),
        ("parsing", "🔍 Parsing Document"),
        ("quality_check", "⚖️ Quality Check"),
        ("normalized", "🧹 Normalizing Content"),
        ("chunking", "✂️ Semantic Chunking"),
        ("embedding", "🧠 Generating Embeddings"),
        ("indexing", "🗂️ Indexing in Qdrant"),
        ("ready", "✅ Ready for RAG Chat")
    ]
    
    status_placeholder = st.empty()
    timeline_placeholder = st.empty()
    
    # Poll status (increase range to 120 to allow time for first-run Docling downloads/processing)
    for _ in range(120): # Poll up to 120 times (3 mins max)
        try:
            res = httpx.get(f"{API_URL}/v1/documents/{job['tenant_id']}/{job['document_id']}", timeout=10.0)
            if res.status_code == 200:
                doc_status = res.json()["status"]
                
                # Check for failure states
                if doc_status in ["permanent_failure", "retryable_failure"]:
                    status_placeholder.error(f"Pipeline Failed! Error Status: {doc_status}")
                    break
                    
                # Find current stage index
                current_idx = -1
                for idx, (stage_val, _) in enumerate(stages):
                    if doc_status == stage_val:
                        current_idx = idx
                        break
                
                # Fallback matching if state is intermediate
                if current_idx == -1 and doc_status in ["validated", "stored", "queued"]:
                    current_idx = 0
                elif current_idx == -1 and doc_status in ["parsed"]:
                    current_idx = 1
                elif current_idx == -1 and doc_status in ["chunked"]:
                    current_idx = 4
                elif current_idx == -1 and doc_status in ["embedded"]:
                    current_idx = 5
                
                # Render Timeline HTML
                timeline_html = "<div style='display: flex; justify-content: space-between; align-items: center; overflow-x: auto; padding: 20px 0;'>"
                for idx, (_, label) in enumerate(stages):
                    if idx < current_idx:
                        # Completed stage
                        color = "#10B981" # Green
                        border = "2px solid #10B981"
                    elif idx == current_idx:
                        # Active stage
                        color = "#6366F1" # Indigo
                        border = "2px dashed #6366F1"
                    else:
                        # Pending stage
                        color = "#475569" # Slate
                        border = "2px solid #334155"
                        
                    timeline_html += f"<div style='flex: 1; text-align: center; min-width: 120px; padding: 10px; margin: 0 5px; border-radius: 8px; border: {border}; background-color: rgba(30, 41, 59, 0.25);'><span style='color: {color}; font-weight: 600; display: block;'>{label}</span></div>"
                timeline_html += "</div>"
                
                timeline_placeholder.markdown(timeline_html, unsafe_allow_html=True)
                status_placeholder.info(f"Current Pipeline Stage: {doc_status.upper()}")
                
                if doc_status == "ready":
                    status_placeholder.success("Document successfully processed and active in vector index!")
                    break
            else:
                status_placeholder.warning("Waiting for worker thread to start job...")
        except Exception as e:
            status_placeholder.error(f"Error tracking pipeline: {str(e)}")
            
        time.sleep(1.5)

# Ingestion History Table
st.markdown("---")
st.markdown("### 📋 Recent Ingestion History")

def get_ingestion_history():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT filename, tenant_id, collection_id, status, created_at FROM documents ORDER BY created_at DESC LIMIT 10",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

df_hist = get_ingestion_history()
if not df_hist.empty:
    status_map = {
        "ready": "✅ Ready",
        "queued": "📥 Queued",
        "parsing": "🔍 Parsing",
        "quality_check": "⚖️ Quality Check",
        "normalized": "🧹 Normalized",
        "chunking": "✂️ Chunking",
        "embedding": "🧠 Embedding",
        "indexing": "🗂️ Indexing",
        "permanent_failure": "❌ Failed",
        "retryable_failure": "⚠️ Retryable",
        "needs_review": "👀 Needs Review"
    }
    df_hist["status"] = df_hist["status"].map(lambda x: status_map.get(str(x).lower(), str(x).upper()))
    df_hist.columns = ["Filename", "Tenant", "Collection ID", "Ingestion Status", "Uploaded At"]
    
    st.dataframe(
        df_hist,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No documents have been uploaded to the pipeline database yet.")


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
