from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
import json
import uuid
from .schemas import IngestResponse
from .dependencies import get_worker_pool, get_state_manager, get_blob_store, get_metadata_store
from ..core.models import DocumentStatus
from ..observability.logging import get_logger
from ..observability.metrics import docs_ingested_total

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])
logger = get_logger("api.ingest")

@router.post("", response_model=IngestResponse, status_code=202)
async def ingest_document(
    tenant_id: str = Form(...),
    collection_id: str = Form("default"),
    file: UploadFile = File(...),
    tags: str = Form("[]"),
    worker_pool = Depends(get_worker_pool),
    state_manager = Depends(get_state_manager),
    blob_store = Depends(get_blob_store),
    metadata_store = Depends(get_metadata_store)
):
    """
    Ingests a document asynchronously.
    Returns 202 Accepted immediately with a job ID.
    """
    try:
        tag_list = json.loads(tags)
    except json.JSONDecodeError:
        tag_list = []
        
    # Ensure tenant exists (auto-create for demo)
    await metadata_store.create_tenant_if_not_exists(tenant_id, f"Tenant {tenant_id}")
    
    file_bytes = await file.read()
    
    # 1. Initialize document in state machine
    document_id, version_id, is_duplicate = await state_manager.initialize_document(
        tenant_id=tenant_id,
        collection_id=collection_id,
        filename=file.filename or "unnamed",
        file_bytes=file_bytes,
        tags=tag_list
    )
    
    # 2. Store raw blob
    await blob_store.save_document(
        tenant_id=tenant_id,
        document_id=document_id,
        version_id=version_id,
        file_bytes=file_bytes,
        filename=file.filename or "unnamed"
    )
    
    # 3. Submit to async worker pool
    await worker_pool.submit_job(
        document_id=document_id,
        version_id=version_id,
        tenant_id=tenant_id,
        filename=file.filename or "unnamed"
    )
    
    docs_ingested_total.labels(tenant_id=tenant_id, status="accepted").inc()
    
    return IngestResponse(
        job_id=str(uuid.uuid4()), # Placeholder job ID for now
        document_id=document_id,
        tenant_id=tenant_id,
        collection_id=collection_id,
        version_id=version_id,
        status=DocumentStatus.QUEUED.value,
        message="Document queued for processing."
    )
