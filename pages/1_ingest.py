import streamlit as st
import httpx
import time
import os

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
        background-color: rgba(30, 41, 59, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        color: #94A3B8 !important;
        margin-bottom: 4px !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(99, 102, 241, 0.15) !important;
        color: #F8FAFC !important;
        transform: translateX(4px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.25) 0%, rgba(139, 92, 246, 0.2) 100%) !important;
        border: 1px solid #6366F1 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 Document Ingestion Pipeline")
st.markdown("Upload documents to your tenant's isolated storage and monitor their stage-by-step processing.")

import sqlite3
import pandas as pd

API_URL = os.getenv("API_URL", "http://localhost:8000")
DB_PATH = "./data/pipeline.db"

def get_active_tenants_and_collections():
    default_tenants = ["Trial 1"]
    tenant_collections_map = {t: ["default", "001"] for t in default_tenants}
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            df_docs = pd.read_sql_query("SELECT DISTINCT tenant_id, collection_id FROM documents", conn)
            if not df_docs.empty:
                for t in df_docs["tenant_id"].unique():
                    if t:
                        if t not in default_tenants:
                            default_tenants.append(t)
                        cols = [c for c in df_docs[df_docs["tenant_id"] == t]["collection_id"].unique() if c]
                        if not cols:
                            cols = ["default"]
                        tenant_collections_map[t] = cols
                        
            df_t = pd.read_sql_query("SELECT DISTINCT tenant_id FROM tenants", conn)
            if not df_t.empty:
                for t in df_t["tenant_id"].unique():
                    if t and t not in default_tenants:
                        default_tenants.append(t)
                        if t not in tenant_collections_map:
                            tenant_collections_map[t] = ["default", "001", "002"]
            conn.close()
        except Exception:
            pass
            
    return default_tenants, tenant_collections_map

tenants_list, tenant_collections_map = get_active_tenants_and_collections()

# Input forms
col_inputs, col_upload = st.columns([1, 2])

with col_inputs:
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

with col_upload:
    uploaded_file = st.file_uploader("Choose a file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    if st.button("Start Ingestion Pipeline 🚀", use_container_width=True):
        with st.spinner("Uploading document to backend..."):
            try:
                # Prepare payload
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {
                    "tenant_id": tenant_id,
                    "collection_id": collection_id,
                    "document_type": document_type
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
