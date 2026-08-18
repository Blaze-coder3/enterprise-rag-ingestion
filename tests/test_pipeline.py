import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.rag_pipeline.chunking.semantic import SemanticChunker
from src.rag_pipeline.parsers.docling_adapter import DoclingAdapter
from src.rag_pipeline.tenant.fairness import TenantFairScheduler
from src.rag_pipeline.core.ingest_service import ingest
from src.rag_pipeline.core.models import DocumentStatus

@pytest.mark.asyncio
async def test_ingest_service():
    class MockStateManager:
        async def initialize_document(self, **kwargs):
            return "doc_1", "ver_1", False
            
    class MockBlobStore:
        async def save_document(self, **kwargs):
            pass
            
    class MockWorkerPool:
        async def submit_job(self, **kwargs):
            pass
            
    class MockMetadataStore:
        async def create_tenant_if_not_exists(self, tenant_id, name):
            pass
            
    result = await ingest(
        file_bytes=b"test",
        filename="test.txt",
        document_id="doc_1",
        tenant_id="t1",
        collection_id="default",
        document_type=None,
        tags=[],
        metadata={},
        state_manager=MockStateManager(),
        blob_store=MockBlobStore(),
        metadata_store=MockMetadataStore(),
        worker_pool=MockWorkerPool()
    )
    
    assert result.document_id == "doc_1"
    assert result.status == DocumentStatus.QUEUED

def test_semantic_chunker_token_counting():
    """Verify chunker accurately counts tokens using tiktoken."""
    chunker = SemanticChunker()
    text = "Hello world! This is a simple test sentence for checking token boundaries."
    tokens = chunker._count_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)

@pytest.mark.asyncio
async def test_tenant_fair_scheduler():
    """Verify tenant fair scheduler locks concurrency per tenant."""
    scheduler = TenantFairScheduler(default_concurrency=1)
    
    # Acquire first slot (should succeed immediately)
    await scheduler.acquire("tenant-1")
    
    # Try to acquire second slot (should block)
    try:
        await asyncio.wait_for(scheduler.acquire("tenant-1"), timeout=0.1)
        assert False, "Should have blocked because concurrency is 1"
    except asyncio.TimeoutError:
        pass # Expected blocking behavior
        
    # Release and re-acquire
    scheduler.release("tenant-1")
    await asyncio.wait_for(scheduler.acquire("tenant-1"), timeout=0.1)
    scheduler.release("tenant-1")

@pytest.mark.asyncio
async def test_docling_parser_init():
    """Verify docling parser adapter initialization."""
    parser = DoclingAdapter()
    assert parser.name == "docling"
    assert parser.version.startswith("2.")
