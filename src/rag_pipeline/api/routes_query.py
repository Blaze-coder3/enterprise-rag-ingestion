from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from .dependencies import get_container
from ..retrieval.query_engine import QueryEngine, RetrievedChunk

router = APIRouter(prefix="/v1/query", tags=["retrieval"])

class QueryRequest(BaseModel):
    tenant_id: str
    query: str
    top_k: int = 10
    collection_id: Optional[str] = None

class QueryResponse(BaseModel):
    results: List[dict]
    
@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest, container = Depends(get_container)):
    """Raw retrieval endpoint (no LLM generation)."""
    
    query_engine = QueryEngine(container.vector_store, container.embedder)
    
    chunks = await query_engine.hybrid_search(
        tenant_id=request.tenant_id,
        query_text=request.query,
        top_k=request.top_k,
        collection_id=request.collection_id
    )
    
    results = []
    for chunk in chunks:
        results.append({
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "score": chunk.score,
            "page_numbers": chunk.page_numbers,
            "section_hierarchy": chunk.section_hierarchy
        })
        
    return QueryResponse(results=results)
