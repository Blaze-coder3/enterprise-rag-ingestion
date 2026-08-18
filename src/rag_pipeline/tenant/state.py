from typing import Tuple, List, Optional
import uuid
import datetime
import hashlib
from ..core.models import DocumentStatus
from ..core.exceptions import RagPipelineError
from ..storage.metadata_store import MetadataStore
from ..storage.db_models import DocumentModel, DocumentVersionModel

# ── Legal state transitions ────────────────────────────────────────
# Key = current status, Value = set of statuses it may transition to.
VALID_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.QUEUED:             {DocumentStatus.PARSING, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.PARSING:            {DocumentStatus.QUALITY_CHECK, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.QUALITY_CHECK:      {DocumentStatus.NORMALIZED, DocumentStatus.NEEDS_REVIEW, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.NORMALIZED:         {DocumentStatus.CHUNKING, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.CHUNKING:           {DocumentStatus.EMBEDDING, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.EMBEDDING:          {DocumentStatus.INDEXING, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.INDEXING:           {DocumentStatus.READY, DocumentStatus.RETRYABLE_FAILURE, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.READY:              {DocumentStatus.SUPERSEDED, DocumentStatus.DELETED, DocumentStatus.PARSING},
    DocumentStatus.RETRYABLE_FAILURE:  {DocumentStatus.QUEUED, DocumentStatus.PERMANENT_FAILURE},
    DocumentStatus.NEEDS_REVIEW:       {DocumentStatus.QUEUED, DocumentStatus.DELETED},
    DocumentStatus.SUPERSEDED:         {DocumentStatus.DELETED},
    DocumentStatus.DELETED:            set(),
}


class StateManager:
    """Manages the document state machine, idempotency, and deduplication."""
    
    def __init__(self, metadata_store: MetadataStore):
        self.db = metadata_store
        
    async def initialize_document(
        self,
        tenant_id: str,
        collection_id: str,
        filename: str,
        file_bytes: bytes,
        tags: List[str],
        document_id: str | None = None,
        document_type: str | None = None,
        metadata: dict | None = None,
    ) -> Tuple[str, str, bool]:
        """
        Initializes a document in the state machine.

        Performs content-hash deduplication: if a document with the same
        ``content_hash`` already exists for this tenant and is in READY state,
        the existing IDs are returned with ``is_duplicate=True``.

        Returns: (document_id, version_id, is_duplicate)
        """
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # ── Deduplication check ─────────────────────────────────────
        existing = await self.db.find_document_by_hash(tenant_id, content_hash)
        if existing and existing.status == DocumentStatus.READY.value:
            return existing.document_id, existing.current_version_id or "", True

        # ── Create new document ─────────────────────────────────────
        doc_id = document_id or str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        
        doc_model = DocumentModel(
            document_id=doc_id,
            tenant_id=tenant_id,
            collection_id=collection_id,
            filename=filename,
            document_type=document_type,
            status=DocumentStatus.QUEUED.value,
            current_version_id=version_id,
            content_hash=content_hash,
            tags=tags,
            metadata_dict=metadata
        )
        
        version_model = DocumentVersionModel(
            version_id=version_id,
            document_id=doc_id,
            content_hash=content_hash,
            status=DocumentStatus.QUEUED.value
        )
        
        await self.db.create_document(doc_model)
        await self.db.create_version(version_model)
        
        return doc_id, version_id, False
        
    async def transition(self, document_id: str, version_id: str, new_status: DocumentStatus) -> None:
        """
        Transitions a document to a new state after validating the transition
        is legal according to the state machine graph.
        """
        current = await self.db.get_document_by_id(document_id)
        if current:
            current_status = DocumentStatus(current.status)
            allowed = VALID_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                raise RagPipelineError(
                    f"Illegal state transition: {current_status.value} → {new_status.value} "
                    f"(allowed: {[s.value for s in allowed]})"
                )
        await self.db.update_document_status(document_id, new_status.value, version_id)
