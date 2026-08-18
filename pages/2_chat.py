import streamlit as st
import httpx
import os

st.set_page_config(page_title="Enterprise Chat", page_icon="💬", layout="wide")

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
    /* Style citation cards */
    .citation-card {
        background-color: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 12px;
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

st.title("💬 Tenant Conversational Search")
st.markdown("Query your documents with real-time semantic grounding and citations.")

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

# Setup sidebar configs
with st.sidebar:
    st.header("Workspace Config")
    
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

    # Track current active workspace to automatically reset chat when switching tenants/collections
    current_workspace = f"{tenant_id}::{collection_id}"
    if st.session_state.get("active_workspace") != current_workspace:
        st.session_state["active_workspace"] = current_workspace
        st.session_state["messages"] = []
        st.session_state["citations"] = []

    if st.button("Clear Chat History"):
        st.session_state["messages"] = []
        st.session_state["citations"] = []
        st.rerun()

# Layout: Split screen side-by-side
col_chat, col_citations = st.columns([1.2, 0.8])

# Chat session state initialization
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "citations" not in st.session_state:
    st.session_state["citations"] = []

# Left side: Conversation
with col_chat:
    st.subheader("Discussion Thread")
    
    # Render chat messages
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Append user message
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.spinner("Retrieving sources & generating answer..."):
            try:
                # Call backend chat service
                payload = {
                    "tenant_id": tenant_id,
                    "message": prompt,
                    "collection_id": collection_id if collection_id else None
                }
                
                res = httpx.post(f"{API_URL}/v1/chat", json=payload, timeout=60.0)
                if res.status_code == 200:
                    chat_data = res.json()
                    
                    # Update conversation and active citations
                    st.session_state["messages"].append({"role": "assistant", "content": chat_data["content"]})
                    st.session_state["citations"] = chat_data["citations"]
                    
                    st.rerun()
                else:
                    st.error(f"Chat API failed: {res.text}")
            except Exception as e:
                st.error(f"Error communicating with Chat API: {str(e)}")

# Right side: Grounded Citation Inspector
with col_citations:
    st.subheader("🔍 Grounded Source Inspector")
    st.markdown("Below are the exact document segments and page references retrieved from Qdrant vector store used to ground the LLM's answer.")
    
    citations = st.session_state["citations"]
    if not citations:
        st.info("No sources retrieved yet. Submit a query to inspect grounding context.")
    else:
        for idx, cit in enumerate(citations, 1):
            st.markdown(f"""
            <div class="citation-card">
                <span style="color: #6366F1; font-weight: bold; font-size: 0.95rem;">📄 Source {idx}: {cit['document_id'][:8]}... ({cit['section']})</span>
                <p style="color: #F1F5F9; font-size: 0.9rem; margin-top: 5px;">"{cit['content_snippet']}"</p>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #94A3B8; margin-top: 8px;">
                    <span><b>Pages:</b> {', '.join(map(str, cit['page_numbers'])) if cit['page_numbers'] else 'N/A'}</span>
                    <span><b>Doc ID:</b> {cit['document_id']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
