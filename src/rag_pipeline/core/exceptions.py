class RagPipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass

class ValidationException(RagPipelineError):
    """Raised when a document fails initial validation."""
    pass

class IdempotencyException(RagPipelineError):
    """Raised when a document is already being processed or has been processed."""
    pass

class StorageException(RagPipelineError):
    """Raised when writing to or reading from blob/metadata storage fails."""
    pass

class ParsingException(RagPipelineError):
    """Raised when a parser fails to process a document."""
    pass

class NormalizationException(RagPipelineError):
    """Raised when a parser's output cannot be normalized to CanonicalDocument."""
    pass

class ChunkingException(RagPipelineError):
    """Raised when chunking fails."""
    pass

class EmbeddingException(RagPipelineError):
    """Raised when generating embeddings fails."""
    pass

class IndexingException(RagPipelineError):
    """Raised when upserting chunks to the vector store fails."""
    pass

class TenantIsolationException(RagPipelineError):
    """Raised when tenant context is missing or violated."""
    pass
