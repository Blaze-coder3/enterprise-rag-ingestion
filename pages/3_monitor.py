import streamlit as st
import sqlite3
import pandas as pd
import os

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
        
        # 2. Ragas Evaluation Metrics
        st.subheader("🤖 Ragas LLM Generation Evaluations")
        
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
            
        st.divider()
        
        # 3. Ingestion Charts
        st.subheader("Document Ingestion Status")
        if total_docs > 0:
            status_counts = df_docs['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            st.bar_chart(status_counts.set_index('Status'))
        else:
            st.info("No documents found to chart.")
            
        st.divider()
        
        # 4. Pipeline Decisions & Quality Check Logs
        st.subheader("Recent Policy & Routing Decisions")
        df_decisions = pd.read_sql_query(
            "SELECT tenant_id, stage, decision, reason FROM decision_events ORDER BY rowid DESC LIMIT 10", 
            conn
        )
        if not df_decisions.empty:
            st.dataframe(df_decisions, width="stretch")
        else:
            st.info("No decision logging events recorded yet.")
            
        # 5. Pipeline stage timing
        st.subheader("Ingestion Stage Performance")
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
            
        conn.close()
    except Exception as e:
        st.error(f"Error loading metrics: {str(e)}")
