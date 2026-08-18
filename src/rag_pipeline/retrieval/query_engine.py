import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from qdrant_client.http import models
from ..storage.vector_store import VectorStore
from ..embeddings.base import BaseEmbedder
from ..core.models import Chunk
from ..observability.logging import get_logger
from ..observability.tracing import get_tracer
from ..observability.metrics import query_latency_seconds, retrieval_results_count

logger = get_logger("query_engine")
tracer = get_tracer("rag_pipeline")

class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    tenant_id: str
    content: str
    score: float
    page_numbers: List[int]
    section_hierarchy: List[str]
    metadata: Dict[str, Any]

class QueryEngine:
    def __init__(self, vector_store: VectorStore, embedder: BaseEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder
        
    async def hybrid_search(self, tenant_id: str, query_text: str, top_k: int = 10, collection_id: Optional[str] = None) -> List[RetrievedChunk]:
        """Performs hybrid search using Qdrant native prefetch + RRF."""
        start_time = time.time()
        
        with tracer.start_as_current_span("hybrid_search") as span:
            span.set_attribute("tenant_id", tenant_id)
            
            # Embed query. We mock this as a chunk to use our embedder easily.
            # In a real app we'd have a specific embed_query method.
            dummy_chunk = Chunk(
                chunk_id="query",
                document_id="query",
                version_id="query",
                tenant_id=tenant_id,
                collection_id="query",
                content=query_text,
                content_hash="",
                chunk_index=0,
                token_count=0,
                page_numbers=[],
                node_type="query",
                section_id="query",
                embedding_model="",
                embedding_version=""
            )
            await self.embedder.embed_batch([dummy_chunk])
            
            dense_vector = dummy_chunk.dense_embedding
            sparse_vector = dummy_chunk.sparse_embedding
            
            # Build filters for multitenancy + active status
            must_filters = [
                models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id)),
                models.FieldCondition(key="status", match=models.MatchValue(value="active"))
            ]
            
            if collection_id:
                must_filters.append(
                    models.FieldCondition(key="collection_id", match=models.MatchValue(value=collection_id))
                )
                
            tenant_filter = models.Filter(must=must_filters)
            
            # Qdrant Query API using Prefetch + RRF Fusion
            prefetch_queries = []
            
            if dense_vector:
                prefetch_queries.append(
                    models.Prefetch(
                        query=dense_vector,
                        using="dense",
                        limit=top_k * 2
                    )
                )
                
            if sparse_vector:
                prefetch_queries.append(
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_vector.indices,
                            values=sparse_vector.values
                        ),
                        using="sparse",
                        limit=top_k * 2
                    )
                )
                
            results = await self.vector_store.client.query_points(
                collection_name=self.vector_store.collection_name,
                prefetch=prefetch_queries,
                query=models.FusionQuery(
                    fusion=models.Fusion.RRF
                ),
                query_filter=tenant_filter,
                limit=top_k,
                with_payload=True
            )
            
            retrieved = []
            for point in results.points:
                payload = point.payload or {}
                retrieved.append(RetrievedChunk(
                    chunk_id=payload.get("chunk_id", ""),
                    document_id=payload.get("document_id", ""),
                    tenant_id=payload.get("tenant_id", ""),
                    content=payload.get("content", ""),
                    score=point.score,
                    page_numbers=payload.get("page_numbers", []),
                    section_hierarchy=payload.get("section_hierarchy", []),
                    metadata=payload.get("metadata", {})
                ))
                
            latency = time.time() - start_time
            query_latency_seconds.labels(tenant_id=tenant_id).observe(latency)
            retrieval_results_count.observe(len(retrieved))
            
            return retrieved
