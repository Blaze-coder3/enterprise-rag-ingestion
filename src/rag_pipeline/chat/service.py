import time
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from .memory import ConversationMemory
from ..retrieval.query_engine import QueryEngine, RetrievedChunk
from ..observability.logging import get_logger
from ..observability.tracing import get_tracer
from ..evaluation.evaluator import RagasEvaluator

logger = get_logger("chat_service")
tracer = get_tracer("rag_pipeline")

class Citation(BaseModel):
    chunk_id: str
    document_id: str
    content_snippet: str
    page_numbers: List[int]
    section: str

class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    citations: List[Citation]
    model_used: str
    latency_ms: float

class ChatService:
    def __init__(self, memory: ConversationMemory, query_engine: QueryEngine):
        self.memory = memory
        self.query_engine = query_engine
        
    async def chat(self, tenant_id: str, message: str, conversation_id: Optional[str] = None, collection_id: Optional[str] = None) -> ChatResponse:
        start_time = time.time()
        
        with tracer.start_as_current_span("chat_turn") as span:
            span.set_attribute("tenant_id", tenant_id)
            
            # 1. Get or create conversation
            conv_id = await self.memory.get_or_create_conversation(tenant_id, conversation_id)
            
            # 2. Add user message to history
            await self.memory.add_message(conv_id, "user", message)
            
            # 3. Retrieve relevant chunks
            chunks = await self.query_engine.hybrid_search(
                tenant_id=tenant_id,
                query_text=message,
                top_k=5,
                collection_id=collection_id
            )
            
            # 4. Generate answer (Real or Mock LLM)
            import os
            import openai
            from google import genai
            
            llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
            openai_key = os.getenv("OPENAI_API_KEY")
            gemini_key = os.getenv("GEMINI_API_KEY")
            
            citations = []
            for idx, chunk in enumerate(chunks, 1):
                section = " > ".join(chunk.section_hierarchy) if chunk.section_hierarchy else "Document Body"
                page_ref = f"p.{chunk.page_numbers[0]}" if chunk.page_numbers else "unknown page"
                snippet = chunk.content[:150].replace('\n', ' ') + "..." if len(chunk.content) > 150 else chunk.content
                citations.append(Citation(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    content_snippet=snippet,
                    page_numbers=chunk.page_numbers,
                    section=section
                ))
            
            # Format context for the prompt
            context_str = "\n\n".join([f"[Source: {c.document_id}, Page: {c.page_numbers[0] if c.page_numbers else 'N/A'}] {c.content}" for c in chunks])
            
            system_prompt = (
                "You are an enterprise AI assistant. Answer questions strictly based on the provided context. "
                "Do not use external knowledge or assumptions. Cite sources as [Source: <doc_id>, p.<page_num>]. "
                "If the provided context does not contain sufficient facts to answer the question, state: "
                "\"I could not find sufficient information in the provided context to answer your question.\" "
                "Respond in clear, professional English."
            )
            
            user_content = f"Context:\n{context_str}\n\nQuestion: {message}"
            chat_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            generated_content = ""
            model_used = "mock-llm-v1"
            
            if llm_provider == "openai" and openai_key:
                try:
                    client = openai.AsyncOpenAI(api_key=openai_key)
                    completion = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=chat_messages
                    )
                    generated_content = completion.choices[0].message.content
                    model_used = "gpt-4o-mini"
                except Exception as e:
                    logger.error("Failed to generate answer with OpenAI", error=str(e))
                    
            elif llm_provider == "gemini" and gemini_key:
                try:
                    client = genai.Client(api_key=gemini_key)
                    loop = asyncio.get_event_loop()
                    full_prompt = f"{system_prompt}\n\n{user_content}"
                    response = await loop.run_in_executor(
                        None,
                        lambda: client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=full_prompt
                        )
                    )
                    generated_content = response.text
                    model_used = "gemini-2.5-flash"
                except Exception as e:
                    logger.error("Failed to generate answer with Gemini", error=str(e))
                    
            elif llm_provider == "ollama":
                try:
                    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                    ollama_model = os.getenv("LLM_MODEL", "phi3")
                    client = openai.AsyncOpenAI(base_url=ollama_url, api_key="ollama")
                    completion = await client.chat.completions.create(
                        model=ollama_model,
                        messages=chat_messages
                    )
                    generated_content = completion.choices[0].message.content
                    model_used = f"ollama-{ollama_model}"
                except Exception as e:
                    logger.error("Failed to generate answer with Ollama", error=str(e))

            if not generated_content:
                answer_parts = [f"Based on the documents (Mock Mode, set LLM_PROVIDER & API key to enable real generation), here is what I found regarding '{message}':\n"]
                if not chunks:
                    answer_parts.append("I could not find any relevant information in the uploaded documents.")
                else:
                    for cit in citations:
                        page_ref = f"p.{cit.page_numbers[0]}" if cit.page_numbers else "unknown page"
                        answer_parts.append(f"• {cit.content_snippet} [Source: {cit.document_id}, {page_ref}]\n")
                generated_content = "\n".join(answer_parts)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 5. Save assistant message
            chunk_ids = [c.chunk_id for c in chunks]
            msg_id = await self.memory.add_message(
                conversation_id=conv_id,
                role="assistant",
                content=generated_content,
                retrieved_chunk_ids=chunk_ids,
                model_used=model_used,
                latency_ms=latency_ms
            )
            
            # 6. Asynchronously trigger Ragas evaluation task
            try:
                evaluator = RagasEvaluator(self.memory.db)
                asyncio.create_task(
                    evaluator.evaluate_turn(
                        tenant_id=tenant_id,
                        conversation_id=conv_id,
                        message_id=msg_id,
                        question=message,
                        answer=generated_content,
                        context_chunks=[c.content for c in chunks],
                        latency_ms=latency_ms
                    )
                )
            except Exception as eval_err:
                logger.error("Failed to schedule Ragas evaluation", error=str(eval_err))
            
            return ChatResponse(
                conversation_id=conv_id,
                message_id=msg_id,
                content=generated_content,
                citations=citations,
                model_used=model_used,
                latency_ms=latency_ms
            )
