import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.rag_pipeline.chunking.semantic import SemanticChunker
from src.rag_pipeline.parsers.docling_adapter import DoclingAdapter
from src.rag_pipeline.tenant.fairness import TenantFairScheduler

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
