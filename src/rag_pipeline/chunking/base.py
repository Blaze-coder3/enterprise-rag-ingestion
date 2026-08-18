from typing import Protocol, List
from ..core.models import CanonicalDocument, Chunk

class ChunkConfig:
    def __init__(self, target_tokens: int = 512, overlap_tokens: int = 50):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

class BaseChunker(Protocol):
    def chunk(self, doc: CanonicalDocument, config: ChunkConfig) -> List[Chunk]:
        """Convert a CanonicalDocument into a list of Chunk objects."""
        ...
