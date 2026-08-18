import json
from typing import List, Optional, Any, Dict
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from ..core.models import Chunk
from ..config import settings

class VectorStore:
    """Qdrant wrapper using single collection with named vectors for Hybrid Search."""
    
    def __init__(self, collection_name: str = "documents_v1"):
        self.collection_name = collection_name
        
        # Configure client based on settings
        if settings.qdrant_api_key:
            self.client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        else:
            self.client = AsyncQdrantClient(url=settings.qdrant_url)
            
    async def initialize(self) -> None:
        """Create collection and indexes if they don't exist."""
        exists = await self.client.collection_exists(collection_name=self.collection_name)
        
        if not exists:
            # Create collection with named vectors for dense and sparse
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        modifier=models.Modifier.IDF
                    )
                }
            )
            
            # Create payload indexes for filtering
            # tenant_id is MANDATORY for multitenancy
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="tenant_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="collection_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="status",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="access_groups",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

    async def upsert_chunks(self, chunks: List[Chunk]) -> None:
        """Upsert a batch of chunks into Qdrant."""
        if not chunks:
            return
            
        points = []
        for chunk in chunks:
            vectors = {}
            if chunk.dense_embedding:
                vectors["dense"] = chunk.dense_embedding
            if chunk.sparse_embedding:
                vectors["sparse"] = models.SparseVector(
                    indices=chunk.sparse_embedding.indices,
                    values=chunk.sparse_embedding.values
                )
                
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "version_id": chunk.version_id,
                "tenant_id": chunk.tenant_id,
                "collection_id": chunk.collection_id,
                "content": chunk.content,
                "content_hash": chunk.content_hash,
                "chunk_index": chunk.chunk_index,
                "page_numbers": chunk.page_numbers,
                "node_type": chunk.node_type,
                "section_hierarchy": chunk.section_hierarchy,
                "section_id": chunk.section_id,
                "parent_chunk_id": chunk.parent_chunk_id,
                "embedding_model": chunk.embedding_model,
                "embedding_version": chunk.embedding_version,
                "tags": chunk.tags,
                "access_groups": chunk.access_groups,
                "document_type": chunk.document_type,
                "status": chunk.status,
                # Convert bounding boxes to dicts for JSON serialization
                "bounding_boxes": [bb.model_dump() for bb in chunk.bounding_boxes],
                # Extensible metadata
                "metadata": chunk.metadata
            }
            
            points.append(
                models.PointStruct(
                    # Qdrant requires UUID or uint64 for IDs.
                    # We hash our chunk_id to UUID format for consistency
                    id=self._generate_uuid_from_string(chunk.chunk_id),
                    vector=vectors,
                    payload=payload
                )
            )
            
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
    async def delete_document(self, tenant_id: str, document_id: str) -> None:
        """Soft deletes a document by updating status to 'superseded' or 'deleted'."""
        await self.client.set_payload(
            collection_name=self.collection_name,
            payload={"status": "deleted"},
            points=models.Filter(
                must=[
                    models.FieldCondition(
                        key="tenant_id", match=models.MatchValue(value=tenant_id)
                    ),
                    models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    )
                ]
            )
        )
        
    def _generate_uuid_from_string(self, text: str) -> str:
        """Converts any string to a consistent UUID format string."""
        import hashlib
        import uuid
        m = hashlib.md5()
        m.update(text.encode('utf-8'))
        return str(uuid.UUID(m.hexdigest()))
