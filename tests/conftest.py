import pytest
import sqlite3
from unittest.mock import MagicMock

@pytest.fixture
def mock_embedding_client():
    """Provides a fake embedding generator that returns static float arrays instantly."""
    client = MagicMock()
    # Mock an async batch generator returning mock 384-dimensional vectors
    async def fake_batch_embed(texts):
        return [[0.1] * 384 for _ in texts]
    client.generate_embeddings_batch = fake_batch_embed
    return client

@pytest.fixture
def in_memory_db():
    """Provides an isolated SQLite database running entirely in RAM for clean state resets."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # Initialize your multi-tenant tracking schema
    cursor.execute("""
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, tenant_id TEXT, user_id TEXT,
            filename TEXT, file_type TEXT, ingestion_status TEXT, 
            confidence_score REAL, fallback_triggered INTEGER
        )
    """)
    conn.commit()
    yield conn
    conn.close()
