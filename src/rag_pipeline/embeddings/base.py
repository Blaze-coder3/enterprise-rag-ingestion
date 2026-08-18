from typing import Protocol, List
from ..core.models import Chunk

class BaseEmbedder(Protocol):
    async def embed_batch(self, chunks: List[Chunk]) -> None:
        """
        Updates the passed chunks in-place with dense and sparse embeddings.
        Populates:
        - chunk.dense_embedding
        - chunk.sparse_embedding
        - chunk.embedding_model
        - chunk.embedding_version
        """
        ...
        
    @property
    def dense_model_name(self) -> str:
        ...
        
    @property
    def sparse_model_name(self) -> str:
        ...
