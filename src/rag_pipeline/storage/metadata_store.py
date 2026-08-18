import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update
from .db_models import (
    Base, TenantModel, DocumentModel, DocumentVersionModel, 
    PipelineStageRunModel, DecisionEventModel, ChatEvaluationModel
)
from ..config import settings
from ..core.decisions import DecisionEvent
import os

class MetadataStore:
    """SQLAlchemy metadata store."""
    
    def __init__(self):
        # We need async engine. SQLite async requires ai sqlite (which we would add via aiosqlite, 
        # but for simplicity we will assume synchronous sqlite if using default or configure properly)
        
        db_url = settings.database_url
        if db_url.startswith("sqlite:///"):
            # Ensure path exists
            path = db_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            # convert to async sqlite
            db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
            
        self.engine = create_async_engine(db_url, echo=False)
        self.SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    async def initialize(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def create_tenant_if_not_exists(self, tenant_id: str, name: str) -> None:
        async with self.SessionLocal() as session:
            result = await session.execute(select(TenantModel).where(TenantModel.tenant_id == tenant_id))
            tenant = result.scalar_one_or_none()
            if not tenant:
                new_tenant = TenantModel(tenant_id=tenant_id, name=name)
                session.add(new_tenant)
                await session.commit()
                
    async def get_document(self, tenant_id: str, document_id: str) -> Optional[DocumentModel]:
        async with self.SessionLocal() as session:
            result = await session.execute(
                select(DocumentModel).where(
                    DocumentModel.tenant_id == tenant_id,
                    DocumentModel.document_id == document_id
                )
            )
            return result.scalar_one_or_none()
            
    async def create_document(self, doc_model: DocumentModel) -> None:
        async with self.SessionLocal() as session:
            session.add(doc_model)
            await session.commit()
            
    async def update_document_status(self, document_id: str, status: str, version_id: Optional[str] = None) -> None:
        async with self.SessionLocal() as session:
            stmt = update(DocumentModel).where(DocumentModel.document_id == document_id).values(status=status)
            if version_id:
                stmt = stmt.values(current_version_id=version_id)
            await session.execute(stmt)
            
            if version_id:
                await session.execute(
                    update(DocumentVersionModel).where(
                        DocumentVersionModel.version_id == version_id
                    ).values(status=status)
                )
            await session.commit()
            
    async def create_version(self, version_model: DocumentVersionModel) -> None:
        async with self.SessionLocal() as session:
            session.add(version_model)
            await session.commit()
            
    async def record_stage_run(self, run: PipelineStageRunModel) -> None:
        async with self.SessionLocal() as session:
            session.add(run)
            await session.commit()
            
    async def log_decision(self, decision: DecisionEvent) -> None:
        import uuid
        async with self.SessionLocal() as session:
            model = DecisionEventModel(
                event_id=str(uuid.uuid4()),
                trace_id=decision.trace_id,
                document_id=decision.document_id,
                tenant_id=decision.tenant_id,
                stage=decision.stage,
                decision=decision.decision,
                reason=decision.reason,
                policy_version=decision.policy_version,
                input_signals_json=decision.input_signals
            )
            session.add(model)
            await session.commit()
            
    async def log_chat_evaluation(self, eval_model: ChatEvaluationModel) -> None:
        async with self.SessionLocal() as session:
            session.add(eval_model)
            await session.commit()
