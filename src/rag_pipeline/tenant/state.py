from typing import Tuple, List, Optional
import uuid
import datetime
import hashlib
from ..core.models import DocumentStatus
from ..storage.metadata_store import MetadataStore
from ..storage.db_models import DocumentModel, DocumentVersionModel

class StateManager:
    """Manages the document state machine and idempotency."""
    
    def __init__(self, metadata_store: MetadataStore):
        self.db = metadata_store
        
    async def initialize_document(self, tenant_id: str, collection_id: str, 
                                  filename: str, file_bytes: bytes, tags: List[str]) -> Tuple[str, str, bool]:
        """
        Initializes a document in the state machine.
        Returns: (document_id, version_id, is_duplicate)
        """
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # In a real app we'd search for existing docs by name/hash to do true dedup
        # For simplicity, we just create a new one every time unless we wanted strict dedup
        document_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        
        doc_model = DocumentModel(
            document_id=document_id,
            tenant_id=tenant_id,
            collection_id=collection_id,
            filename=filename,
            status=DocumentStatus.QUEUED.value,
            current_version_id=version_id,
            content_hash=content_hash,
            tags=tags
        )
        
        version_model = DocumentVersionModel(
            version_id=version_id,
            document_id=document_id,
            content_hash=content_hash,
            status=DocumentStatus.QUEUED.value
        )
        
        await self.db.create_document(doc_model)
        await self.db.create_version(version_model)
        
        return document_id, version_id, False
        
    async def transition(self, document_id: str, version_id: str, new_status: DocumentStatus) -> None:
        """Transitions document to a new state."""
        await self.db.update_document_status(document_id, new_status.value, version_id)
