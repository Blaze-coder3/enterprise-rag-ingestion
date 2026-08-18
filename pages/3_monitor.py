import streamlit as st
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv(override=True)

st.set_page_config(page_title="Pipeline Monitor", page_icon="📊", layout="wide")

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
</style>
""", unsafe_allow_html=True)

import httpx

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
            import httpx
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

st.title("📊 Operational Pipeline Monitor")
st.markdown("""
This dashboard displays real-time operational statistics and Ragas quality evaluation metrics directly from the RAG database.
""")

# Path to local SQLite database
DB_PATH = "./data/pipeline.db"

if not os.path.exists(DB_PATH):
    st.warning("Metadata database not found. Please upload some documents first to initialize metrics.")
else:
    try:
        # Connect to sqlite
        conn = sqlite3.connect(DB_PATH)
        
        # 1. High Level Metrics
        st.subheader("System Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Ingested Docs
        df_docs = pd.read_sql_query("SELECT * FROM documents", conn)
        total_docs = len(df_docs)
        col1.metric("Total Documents Ingested", total_docs)
        
        # Tenants
        df_tenants = pd.read_sql_query("SELECT * FROM tenants", conn)
        total_tenants = len(df_tenants)
        col2.metric("Active Tenants", total_tenants)
        
        # Failed vs Successful
        ready_docs = len(df_docs[df_docs['status'] == 'ready'])
        col3.metric("Ready (Ingested)", ready_docs)
        
        failed_docs = len(df_docs[df_docs['status'].isin(['permanent_failure', 'retryable_failure'])])
        col4.metric("Failed Ingestions", failed_docs)
        
        st.divider()

        # Create tabs to segment features
        tab_evals, tab_latency, tab_decisions = st.tabs([
            "🤖 Ragas Quality Evaluations", 
            "📈 Ingestion Latency & Status", 
            "📋 Policy & Routing Decisions"
        ])
        
        with tab_evals:
            st.markdown("### LLM Generation Quality Scores")
            try:
                df_evals = pd.read_sql_query("SELECT * FROM chat_evaluations", conn)
                if not df_evals.empty:
                    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                    
                    avg_faith = df_evals['faithfulness'].mean()
                    avg_rel = df_evals['answer_relevance'].mean()
                    avg_prec = df_evals['context_precision'].mean()
                    avg_lat = df_evals['latency_ms'].mean()
                    
                    col_e1.metric("Average Faithfulness", f"{avg_faith:.2f} / 1.0")
                    col_e2.metric("Answer Relevance", f"{avg_rel:.2f} / 1.0")
                    col_e3.metric("Context Precision", f"{avg_prec:.2f} / 1.0")
                    col_e4.metric("Avg Chat Latency", f"{avg_lat:.0f} ms")
                    
                    # Chart Ragas scores over time
                    st.markdown("#### Ragas Scores Trend")
                    df_evals['created_at'] = pd.to_datetime(df_evals['created_at'])
                    df_trend = df_evals.sort_values('created_at')[['created_at', 'faithfulness', 'answer_relevance', 'context_precision']].set_index('created_at')
                    st.line_chart(df_trend)
                else:
                    st.info("No chat interactions recorded yet. Ask a question on the Chat page to generate Ragas evaluations!")
            except Exception as eval_err:
                st.info("No evaluations table present yet. Submit a chat query to initialize Ragas metrics.")
                
        with tab_latency:
            st.markdown("### Ingestion Stage Duration Breakdown")
            # Pipeline stage timing
            df_runs = pd.read_sql_query(
                "SELECT stage, duration_ms FROM pipeline_stage_runs", 
                conn
            )
            if not df_runs.empty:
                stage_avg = df_runs.groupby('stage')['duration_ms'].mean().reset_index()
                stage_avg.columns = ['Stage', 'Average Duration (ms)']
                st.bar_chart(stage_avg.set_index('Stage'))
            else:
                st.info("No pipeline stage execution runs recorded yet.")
                
            st.divider()
            st.markdown("### Document Ingestion Status")
            if total_docs > 0:
                status_counts = df_docs['status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                st.bar_chart(status_counts.set_index('Status'))
            else:
                st.info("No documents found to chart.")
                
        with tab_decisions:
            st.markdown("### Recent Policy & Routing Decisions")
            df_decisions = pd.read_sql_query(
                "SELECT tenant_id, stage, decision, reason FROM decision_events ORDER BY rowid DESC LIMIT 10", 
                conn
            )
            if not df_decisions.empty:
                st.dataframe(df_decisions, use_container_width=True)
            else:
                st.info("No decision logging events recorded yet.")
                
        conn.close()
    except Exception as e:
        st.error(f"Error loading metrics: {str(e)}")

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

