import asyncio
from typing import List
from fastembed import TextEmbedding, SparseTextEmbedding
from .base import BaseEmbedder
from ..core.models import Chunk, SparseVector
from ..config import settings

class FastEmbedder(BaseEmbedder):
    """Dual embedder using FastEmbed for both dense and sparse vectors."""
    
    def __init__(self):
        self._dense_model_name = settings.embedding_model
        self._sparse_model_name = settings.sparse_embedding_model
        
        # Initialize models
        self.dense_model = TextEmbedding(model_name=self._dense_model_name)
        self.sparse_model = SparseTextEmbedding(model_name=self._sparse_model_name)
        
    async def embed_batch(self, chunks: List[Chunk]) -> None:
        if not chunks:
            return
            
        texts = [chunk.content for chunk in chunks]
        
        # FastEmbed operations are CPU-bound, run in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        
        dense_generator = await loop.run_in_executor(None, lambda: list(self.dense_model.embed(texts)))
        sparse_generator = await loop.run_in_executor(None, lambda: list(self.sparse_model.embed(texts)))
        
        for i, chunk in enumerate(chunks):
            chunk.dense_embedding = dense_generator[i].tolist()
            
            # Sparse embedding format conversion
            sparse_result = sparse_generator[i]
            chunk.sparse_embedding = SparseVector(
                indices=sparse_result.indices.tolist(),
                values=sparse_result.values.tolist()
            )
            
            chunk.embedding_model = self._dense_model_name
            chunk.embedding_version = "v1"

    @property
    def dense_model_name(self) -> str:
        return self._dense_model_name
        
    @property
    def sparse_model_name(self) -> str:
        return self._sparse_model_name
