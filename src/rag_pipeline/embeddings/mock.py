import asyncio
from typing import List
import random
from .base import BaseEmbedder
from ..core.models import Chunk, SparseVector
from ..config import settings

class MockEmbedder(BaseEmbedder):
    """Mock embedder for tests and lightweight local running."""
    
    async def embed_batch(self, chunks: List[Chunk]) -> None:
        if not chunks:
            return
            
        # Simulate slight latency
        await asyncio.sleep(0.1)
        
        for chunk in chunks:
            # Generate dummy dense vector (e.g., 384 dims for MiniLM)
            chunk.dense_embedding = [random.random() for _ in range(384)]
            
            # Generate dummy sparse vector
            chunk.sparse_embedding = SparseVector(
                indices=[1, 5, 10, 100],
                values=[0.5, 0.8, 1.2, 0.3]
            )
            
            chunk.embedding_model = "mock-dense"
            chunk.embedding_version = "v1"

    @property
    def dense_model_name(self) -> str:
        return "mock-dense"
        
    @property
    def sparse_model_name(self) -> str:
        return "mock-sparse"
