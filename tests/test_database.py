import pytest
from unittest.mock import MagicMock, AsyncMock
from src.rag_pipeline.retrieval.query_engine import QueryEngine
from src.rag_pipeline.storage.vector_store import VectorStore

@pytest.mark.asyncio
async def test_qdrant_enforces_mandatory_tenant_id_filter():
    # 1. Arrange: Mock the core Qdrant search client wrapper and Embedder
    mock_vector_store = MagicMock(spec=VectorStore)
    mock_vector_store.collection_name = "insurance_chunks"
    
    # We mock query_points to return a dummy result
    mock_qdrant_client = MagicMock()
    mock_results = MagicMock()
    mock_results.points = []
    mock_qdrant_client.query_points = AsyncMock(return_value=mock_results)
    mock_vector_store.client = mock_qdrant_client
    
    mock_embedder = AsyncMock()
    # Mocking the embed_batch to simulate it populating the dummy chunk
    async def mock_embed_batch(chunks):
        for c in chunks:
            c.dense_embedding = [0.1] * 384
            c.sparse_embedding = None
    mock_embedder.embed_batch = mock_embed_batch

    engine = QueryEngine(vector_store=mock_vector_store, embedder=mock_embedder)
    
    tenant_id = "tenant_secure_99"
    user_query = "What are my clinical limits?"

    # 2. Act: Simulate a query wrapper execution layer
    await engine.hybrid_search(tenant_id=tenant_id, query_text=user_query)

    # 3. Assert: Double check that the client's parameters contained the unbypassable filter match argument
    called_args, called_kwargs = mock_qdrant_client.query_points.call_args
    assert "query_filter" in called_kwargs
    
    q_filter = called_kwargs["query_filter"]
    # Check that tenant_id is in the must filters
    tenant_filter_found = False
    for must_condition in q_filter.must:
        if must_condition.key == "tenant_id" and must_condition.match.value == tenant_id:
            tenant_filter_found = True
            break
            
    assert tenant_filter_found, "Mandatory tenant_id filter was not found in the Qdrant query!"
