from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class DecisionEvent(BaseModel):
    """Audit trail record: 'Why did the system do X?'"""
    trace_id: str
    document_id: str
    tenant_id: str
    stage: str                       # e.g., "parser_selection", "quality_gate"
    decision: str                    # e.g., "docling", "needs_review"
    reason: str                      # e.g., "native_pdf, text_density=0.92"
    policy_version: str              # e.g., "parser-router-v1"
    input_signals: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
