import streamlit as st
import httpx
import os
from dotenv import load_dotenv
load_dotenv(override=True)

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
    /* Style citation cards */
    .citation-card {
        background-color: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 12px;
        backdrop-filter: blur(10px);
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

st.title("💬 Tenant Conversational Search")
st.markdown("Query your documents with real-time semantic grounding and citations.")

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
        st.session_state["conversation_id"] = ""
        
        # Recover history from backend
        try:
            res = httpx.get(f"{API_URL}/v1/chat/history/{tenant_id}", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("conversation_id"):
                    st.session_state["conversation_id"] = data["conversation_id"]
                    st.session_state["messages"] = data["messages"]
        except Exception:
            pass

    if st.button("Clear Chat History"):
        st.session_state["messages"] = []
        st.session_state["citations"] = []
        st.session_state["conversation_id"] = ""
        st.rerun()

# Mode switcher tabs
tab_chat, tab_playground = st.tabs(["💬 Conversational Grounded Chat", "🔍 Vector DB Retrieval Playground"])

with tab_chat:
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
                        "collection_id": collection_id if collection_id else None,
                        "conversation_id": st.session_state.get("conversation_id", "") or None
                    }
                    
                    res = httpx.post(f"{API_URL}/v1/chat", json=payload, timeout=60.0)
                    if res.status_code == 200:
                        chat_data = res.json()
                        
                        # Update conversation and active citations
                        st.session_state["messages"].append({"role": "assistant", "content": chat_data["content"]})
                        st.session_state["citations"] = chat_data["citations"]
                        st.session_state["conversation_id"] = chat_data["conversation_id"]
                        
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

with tab_playground:
    st.subheader("🎯 Test Vector Database Retrieval performance")
    st.markdown("Query the vector index directly to analyze chunk layout, confidence scores, and multi-tenant ACL filtering.")
    
    col_play_in, col_play_out = st.columns([1, 1.5])
    
    with col_play_in:
        play_query = st.text_input("Raw Search Query", value="", placeholder="Enter query (e.g. primary care copay)")
        play_topk = st.slider("Retrieval Limit (Top K)", min_value=1, max_value=20, value=5)
        
        st.markdown("##### ⚙️ Pipeline Parameters")
        play_mode = st.radio("Retrieval Mode", ["Hybrid RRF Search", "Dense Vector Search Only", "Sparse (BM25) Only"])
        enable_reranker = st.checkbox("Enable Cross-Encoder Reranker", value=True)
        
        run_search = st.button("Query Vector Database 🔍", use_container_width=True)
        
    with col_play_out:
        if run_search and play_query:
            st.info(f"🔒 **ACL Context Enforced:** tenant_id = `{tenant_id}`, collection_id = `{collection_id}`")
            with st.spinner("Executing retrieval query..."):
                try:
                    payload = {
                        "tenant_id": tenant_id,
                        "query": play_query,
                        "top_k": play_topk,
                        "collection_id": collection_id if collection_id else None
                    }
                    res = httpx.post(f"{API_URL}/v1/query", json=payload, timeout=10.0)
                    if res.status_code == 200:
                        results = res.json().get("results", [])
                        if not results:
                            st.warning("No matching vectors found for this tenant space.")
                        else:
                            st.markdown(f"Found **{len(results)}** chunks:")
                            
                            # Build DataFrame
                            records = []
                            for idx, r in enumerate(results, 1):
                                records.append({
                                    "Rank": idx,
                                    "Score": f"{r['score']:.4f}",
                                    "Pages": ", ".join(map(str, r["page_numbers"])) if r["page_numbers"] else "N/A",
                                    "Section": " > ".join(r["section_hierarchy"]) if r["section_hierarchy"] else "Body",
                                    "Doc ID": r["document_id"][:12] + "..."
                                })
                            st.dataframe(pd.DataFrame(records), hide_index=True)
                            
                            st.divider()
                            st.markdown("##### Chunk Contents & Metadata")
                            for idx, r in enumerate(results, 1):
                                with st.expander(f"📄 Rank {idx} - Score: {r['score']:.4f} (Section: {records[idx-1]['Section']})"):
                                    st.code(r["content"], language="text")
                                    st.json({
                                        "chunk_id": r["chunk_id"],
                                        "document_id": r["document_id"],
                                        "page_numbers": r["page_numbers"],
                                        "section_hierarchy": r["section_hierarchy"]
                                    })
                    else:
                        st.error(f"Failed to query backend: {res.text}")
                except Exception as e:
                    st.error(f"Error querying Vector DB: {str(e)}")
        elif run_search:
            st.warning("Please enter a search query.")
        else:
            st.info("Enter a query and click search to view Vector DB payload matches.")

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

