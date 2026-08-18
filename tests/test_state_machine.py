import pytest
import asyncio
from src.rag_pipeline.tenant.state import StateManager
from src.rag_pipeline.core.models import DocumentStatus
from src.rag_pipeline.core.exceptions import RagPipelineError

class MockMetadataStore:
    def __init__(self):
        self.docs = {}
        self.hashes = {}
        
    async def find_document_by_hash(self, tenant_id: str, content_hash: str):
        key = f"{tenant_id}_{content_hash}"
        return self.hashes.get(key)
        
    async def create_document(self, doc_model):
        self.docs[doc_model.document_id] = doc_model
        
    async def create_version(self, version_model):
        pass
        
    async def get_document_by_id(self, document_id: str):
        return self.docs.get(document_id)
        
    async def update_document_status(self, document_id: str, status: str, version_id: str):
        if document_id in self.docs:
            self.docs[document_id].status = status

@pytest.fixture
def state_manager():
    return StateManager(MockMetadataStore())

@pytest.mark.asyncio
async def test_initialize_document_new(state_manager):
    doc_id, version_id, is_duplicate = await state_manager.initialize_document(
        tenant_id="t1", collection_id="c1", filename="test.pdf", 
        file_bytes=b"hello", tags=[]
    )
    assert not is_duplicate
    assert doc_id is not None
    assert version_id is not None

@pytest.mark.asyncio
async def test_initialize_document_duplicate(state_manager):
    # Setup mock to return an existing ready document
    class MockDoc:
        status = DocumentStatus.READY.value
        document_id = "existing_id"
        current_version_id = "v1"
        
    import hashlib
    h = hashlib.sha256(b"hello").hexdigest()
    state_manager.db.hashes[f"t1_{h}"] = MockDoc()
    
    doc_id, version_id, is_duplicate = await state_manager.initialize_document(
        tenant_id="t1", collection_id="c1", filename="test.pdf", 
        file_bytes=b"hello", tags=[]
    )
    assert is_duplicate
    assert doc_id == "existing_id"
    assert version_id == "v1"

@pytest.mark.asyncio
async def test_valid_transition(state_manager):
    doc_id, version_id, _ = await state_manager.initialize_document(
        tenant_id="t1", collection_id="c1", filename="test.pdf", 
        file_bytes=b"hello", tags=[]
    )
    # QUEUED -> PARSING is valid
    await state_manager.transition(doc_id, version_id, DocumentStatus.PARSING)
    doc = await state_manager.db.get_document_by_id(doc_id)
    assert doc.status == DocumentStatus.PARSING.value

@pytest.mark.asyncio
async def test_invalid_transition(state_manager):
    doc_id, version_id, _ = await state_manager.initialize_document(
        tenant_id="t1", collection_id="c1", filename="test.pdf", 
        file_bytes=b"hello", tags=[]
    )
    # QUEUED -> EMBEDDING is invalid
    with pytest.raises(RagPipelineError, match="Illegal state transition"):
        await state_manager.transition(doc_id, version_id, DocumentStatus.EMBEDDING)
