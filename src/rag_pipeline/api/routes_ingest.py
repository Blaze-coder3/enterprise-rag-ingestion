from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List, Optional
import json
import uuid
from .schemas import IngestResponse
from .dependencies import get_worker_pool, get_state_manager, get_blob_store, get_metadata_store
from ..core.models import DocumentStatus
from ..core.ingest_service import ingest
from ..observability.logging import get_logger

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])
logger = get_logger("api.ingest")

@router.post("", response_model=IngestResponse, status_code=202)
async def ingest_document(
    tenant_id: str = Form(...),
    collection_id: str = Form("default"),
    file: UploadFile = File(...),
    tags: str = Form("[]"),
    document_type: Optional[str] = Form(None),
    metadata: str = Form("{}"),
    worker_pool = Depends(get_worker_pool),
    state_manager = Depends(get_state_manager),
    blob_store = Depends(get_blob_store),
    metadata_store = Depends(get_metadata_store)
):
    """
    Ingests a document asynchronously.
    Returns 202 Accepted immediately with a job ID.
    Delegates to the canonical ``ingest()`` service interface.
    """
    try:
        tag_list = json.loads(tags)
    except json.JSONDecodeError:
        tag_list = []
        
    try:
        meta_dict = json.loads(metadata)
    except json.JSONDecodeError:
        meta_dict = {}

    file_bytes = await file.read()
    document_id = str(uuid.uuid4())

    result = await ingest(
        file_bytes=file_bytes,
        filename=file.filename or "unnamed",
        document_id=document_id,
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_type=document_type,
        tags=tag_list,
        metadata=meta_dict,
        state_manager=state_manager,
        blob_store=blob_store,
        metadata_store=metadata_store,
        worker_pool=worker_pool,
    )

    return IngestResponse(
        job_id=result.job_id,
        document_id=result.document_id,
        tenant_id=result.tenant_id,
        collection_id=result.collection_id,
        version_id=result.version_id,
        status=result.status.value,
        message="Duplicate skipped." if result.warnings else "Document queued for processing.",
    )
