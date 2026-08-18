from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from .dependencies import get_container
from ..chat.memory import ConversationMemory
from ..retrieval.query_engine import QueryEngine
from ..chat.service import ChatService, ChatResponse

router = APIRouter(prefix="/v1/chat", tags=["chat"])

class ChatRequest(BaseModel):
    tenant_id: str
    message: str
    conversation_id: Optional[str] = None
    collection_id: Optional[str] = None

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, container = Depends(get_container)):
    """Conversational endpoint with citation tracking."""
    
    memory = ConversationMemory(container.metadata_store)
    query_engine = QueryEngine(container.vector_store, container.embedder)
    
    chat_service = ChatService(memory, query_engine)
    
    response = await chat_service.chat(
        tenant_id=request.tenant_id,
        message=request.message,
        conversation_id=request.conversation_id,
        collection_id=request.collection_id
    )
    
    return response

class ChatHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[dict]

@router.get("/history/{tenant_id}", response_model=ChatHistoryResponse)
async def get_chat_history(tenant_id: str, container = Depends(get_container)):
    """Fetch the most recent conversation history for a tenant."""
    memory = ConversationMemory(container.metadata_store)
    
    conv_id = await memory.get_latest_conversation(tenant_id)
    if not conv_id:
        return ChatHistoryResponse(conversation_id="", messages=[])
        
    messages = await memory.get_history(conv_id, limit=20)
    return ChatHistoryResponse(conversation_id=conv_id, messages=messages)
