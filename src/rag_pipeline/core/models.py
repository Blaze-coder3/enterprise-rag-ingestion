from enum import Enum
from typing import Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class DocumentStatus(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    STORED = "stored"
    QUEUED = "queued"
    PARSING = "parsing"
    PARSED = "parsed"
    QUALITY_CHECK = "quality_check"
    NORMALIZED = "normalized"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    EMBEDDING = "embedding"
    EMBEDDED = "embedded"
    INDEXING = "indexing"
    INDEXED = "indexed"
    READY = "ready"
    
    # Failures
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    NEEDS_REVIEW = "needs_review"
    
    # Lifecycle
    SUPERSEDED = "superseded"
    DELETED = "deleted"

class BoundingBox(BaseModel):
    page: int
    left: float
    top: float
    right: float
    bottom: float

class NodeType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    FIGURE = "figure"
    LIST_ITEM = "list_item"

class ContentNode(BaseModel):
    node_type: NodeType
    content: str
    page_number: int
    bounding_box: Optional[BoundingBox] = None
    children: List["ContentNode"] = Field(default_factory=list)
    section_id: str
    parent_section_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class TableNode(BaseModel):
    caption: Optional[str] = None
    markdown: str
    rows: List[List[str]]
    page_number: int
    bounding_box: Optional[BoundingBox] = None
    section_id: str

class FigureNode(BaseModel):
    caption: Optional[str] = None
    page_number: int
    bounding_box: Optional[BoundingBox] = None
    section_id: str

class QualityVerdict(str, Enum):
    PASS = "pass"
    FAIL_RETRY_OTHER_PARSER = "fail_retry_other_parser"
    FAIL_PERMANENT = "fail_permanent"
    NEEDS_REVIEW = "needs_review"
    FALLBACK = "fallback"

class ParseQualityMetrics(BaseModel):
    text_density: float = 0.0
    empty_page_ratio: float = 0.0
    table_count: int = 0
    avg_block_length: float = 0.0
    ocr_confidence: Optional[float] = None

class CanonicalDocument(BaseModel):
    document_id: str
    tenant_id: str
    collection_id: str = "default"
    version_id: str
    title: str
    page_count: int
    content_tree: List[ContentNode] = Field(default_factory=list)
    tables: List[TableNode] = Field(default_factory=list)
    figures: List[FigureNode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    parse_quality: ParseQualityMetrics = Field(default_factory=ParseQualityMetrics)
    parser_name: str
    parser_version: str

class SparseVector(BaseModel):
    indices: List[int]
    values: List[float]

class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    version_id: str
    tenant_id: str
    collection_id: str
    content: str
    content_hash: str
    chunk_index: int
    token_count: int
    page_numbers: List[int]
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    node_type: str
    section_hierarchy: List[str] = Field(default_factory=list)
    section_id: str
    parent_chunk_id: Optional[str] = None
    dense_embedding: Optional[List[float]] = None
    sparse_embedding: Optional[SparseVector] = None
    embedding_model: str
    embedding_version: str
    tags: List[str] = Field(default_factory=list)
    document_type: Optional[str] = None
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)

class IngestResult(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    collection_id: str
    version_id: str
    status: DocumentStatus
    content_hash: str
    warnings: List[str] = Field(default_factory=list)
    
    # Populated after processing completes
    parser_used: Optional[str] = None
    parser_version: Optional[str] = None
    chunk_count: Optional[int] = None
    total_tokens: Optional[int] = None
    processing_time_ms: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
