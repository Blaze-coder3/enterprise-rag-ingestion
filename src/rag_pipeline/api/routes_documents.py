from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .schemas import DocumentResponse
from .dependencies import get_metadata_store
from ..storage.metadata_store import MetadataStore

router = APIRouter(prefix="/v1/documents", tags=["documents"])

@router.get("/{tenant_id}/{document_id}", response_model=DocumentResponse)
async def get_document(
    tenant_id: str,
    document_id: str,
    metadata_store: MetadataStore = Depends(get_metadata_store)
):
    """Retrieve document metadata and status."""
    doc = await metadata_store.get_document(tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return DocumentResponse(
        document_id=doc.document_id,
        tenant_id=doc.tenant_id,
        collection_id=doc.collection_id,
        filename=doc.filename,
        status=doc.status,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        tags=doc.tags
    )
