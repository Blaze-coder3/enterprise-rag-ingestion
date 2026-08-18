import uuid
from typing import List
from sqlalchemy import select
from ..storage.metadata_store import MetadataStore
from ..storage.db_models import ConversationModel, MessageModel

class ConversationMemory:
    """Manages conversation history."""
    
    def __init__(self, metadata_store: MetadataStore):
        self.db = metadata_store
        
    async def get_or_create_conversation(self, tenant_id: str, conversation_id: str = None) -> str:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        async with self.db.SessionLocal() as session:
            result = await session.execute(
                select(ConversationModel).where(ConversationModel.conversation_id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            
            if not conv:
                conv = ConversationModel(
                    conversation_id=conversation_id,
                    tenant_id=tenant_id
                )
                session.add(conv)
                await session.commit()
                
        return conversation_id
        
    async def add_message(self, conversation_id: str, role: str, content: str, 
                          retrieved_chunk_ids: List[str] = None, model_used: str = None, latency_ms: float = None) -> str:
        message_id = str(uuid.uuid4())
        
        async with self.db.SessionLocal() as session:
            msg = MessageModel(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                retrieved_chunk_ids=retrieved_chunk_ids,
                model_used=model_used,
                latency_ms=latency_ms
            )
            session.add(msg)
            await session.commit()
            
        return message_id
        
    async def get_history(self, conversation_id: str, limit: int = 10) -> List[dict]:
        async with self.db.SessionLocal() as session:
            result = await session.execute(
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.created_at.desc())
                .limit(limit)
            )
            messages = result.scalars().all()
            
            # Return in chronological order
            return [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(messages)
            ]
