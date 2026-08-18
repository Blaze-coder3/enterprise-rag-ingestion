from functools import lru_cache
from typing import Any
import asyncio
from ..config import settings
from ..storage.metadata_store import MetadataStore
from ..storage.vector_store import VectorStore
from ..storage.blob_store import BlobStore
from ..tenant.state import StateManager
from ..tenant.fairness import TenantFairScheduler
from ..parsers.router import ParserRouter
from ..parsers.normalizer import DocumentNormalizer
from ..chunking.semantic import SemanticChunker
from ..embeddings.sentence_transformer import FastEmbedder
from ..embeddings.mock import MockEmbedder
from ..core.pipeline import PipelineOrchestrator
from ..workers.pipeline_worker import WorkerPool

class Container:
    """Dependency injection container."""
    def __init__(self):
        self.metadata_store = MetadataStore()
        self.vector_store = VectorStore()
        self.blob_store = BlobStore(settings.blob_storage_path)
        
        self.state_manager = StateManager(self.metadata_store)
        self.tenant_scheduler = TenantFairScheduler()
        
        self.parser_router = ParserRouter()
        self.normalizer = DocumentNormalizer()
        self.chunker = SemanticChunker()
        
        # Use mock embedder for tests/speed if needed, but FastEmbed is default
        self.embedder = FastEmbedder()
        
        self.pipeline_orchestrator = PipelineOrchestrator(
            state_manager=self.state_manager,
            metadata_store=self.metadata_store,
            blob_store=self.blob_store,
            parser_router=self.parser_router,
            normalizer=self.normalizer,
            chunker=self.chunker,
            embedder=self.embedder,
            vector_store=self.vector_store,
            tenant_scheduler=self.tenant_scheduler
        )
        
        self.worker_pool = WorkerPool(self.pipeline_orchestrator, num_workers=4)

@lru_cache()
def get_container() -> Container:
    return Container()

def get_metadata_store() -> MetadataStore:
    return get_container().metadata_store

def get_worker_pool() -> WorkerPool:
    return get_container().worker_pool

def get_state_manager() -> StateManager:
    return get_container().state_manager

def get_blob_store() -> BlobStore:
    return get_container().blob_store
