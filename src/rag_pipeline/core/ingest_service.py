"""
Public ingest interface as specified by the assignment contract.

This module exposes the canonical `ingest()` function that serves as the
system's primary entry point for document ingestion.
"""
import hashlib
import uuid
from typing import Optional

from ..core.models import DocumentStatus, IngestResult
from ..observability.logging import get_logger
from ..observability.metrics import docs_ingested_total

logger = get_logger("ingest_service")


async def ingest(
    file_bytes: bytes,
    filename: str,
    document_id: str,
    tenant_id: str,
    collection_id: str,
    document_type: str | None,
    tags: list[str],
    metadata: dict,
    *,
    state_manager,
    blob_store,
    metadata_store,
    worker_pool,
) -> IngestResult:
    """
    Ingests a document into the RAG pipeline.

    This is the canonical interface required by the assignment specification.
    It performs validation, blob storage, state initialization, and submits
    the document for asynchronous processing via the worker pool.

    Args:
        file_bytes: Raw bytes of the uploaded document.
        filename: Original filename including extension.
        document_id: Caller-supplied unique document identifier.
        tenant_id: Tenant namespace for isolation.
        collection_id: Logical collection within the tenant.
        document_type: Optional MIME type or document category hint.
        tags: User-supplied tags for categorization.
        metadata: Arbitrary key-value metadata for extensibility.
        state_manager: Injected StateManager dependency.
        blob_store: Injected BlobStore dependency.
        metadata_store: Injected MetadataStore dependency.
        worker_pool: Injected WorkerPool dependency.

    Returns:
        IngestResult with job tracking information and content hash.
    """
    warnings: list[str] = []
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # Ensure tenant exists
    await metadata_store.create_tenant_if_not_exists(tenant_id, f"Tenant {tenant_id}")

    # Initialize document in state machine (handles dedup)
    doc_id, version_id, is_duplicate = await state_manager.initialize_document(
        tenant_id=tenant_id,
        collection_id=collection_id,
        filename=filename,
        file_bytes=file_bytes,
        tags=tags,
        document_id=document_id,
        document_type=document_type,
        metadata=metadata,
    )

    if is_duplicate:
        warnings.append(f"Duplicate content detected (hash={content_hash[:12]}…). Skipped re-processing.")
        return IngestResult(
            job_id=str(uuid.uuid4()),
            document_id=doc_id,
            tenant_id=tenant_id,
            collection_id=collection_id,
            version_id=version_id,
            status=DocumentStatus.READY,
            content_hash=content_hash,
            warnings=warnings,
        )

    # Store raw blob
    await blob_store.save_document(
        tenant_id=tenant_id,
        document_id=doc_id,
        version_id=version_id,
        file_bytes=file_bytes,
        filename=filename,
    )

    # Submit to async worker pool
    await worker_pool.submit_job(
        document_id=doc_id,
        version_id=version_id,
        tenant_id=tenant_id,
        filename=filename,
    )

    docs_ingested_total.labels(tenant_id=tenant_id, status="accepted").inc()

    logger.info("Document ingested via service", document_id=doc_id, tenant_id=tenant_id)

    return IngestResult(
        job_id=str(uuid.uuid4()),
        document_id=doc_id,
        tenant_id=tenant_id,
        collection_id=collection_id,
        version_id=version_id,
        status=DocumentStatus.QUEUED,
        content_hash=content_hash,
        warnings=warnings,
    )
