from pydantic import BaseModel, Field
from typing import List, Optional, Any
from ..core.models import DocumentStatus

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    document_type: Optional[str] = None

class IngestResponse(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    collection_id: str
    version_id: str
    status: str
    message: str

class DocumentResponse(BaseModel):
    document_id: str
    tenant_id: str
    collection_id: str
    filename: str
    status: str
    created_at: str
    updated_at: str
    tags: List[str]

class HealthResponse(BaseModel):
    status: str
    components: dict[str, str]
