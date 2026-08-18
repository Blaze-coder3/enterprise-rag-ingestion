import time
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from .memory import ConversationMemory
from ..retrieval.query_engine import QueryEngine, RetrievedChunk
from ..observability.logging import get_logger
from ..observability.tracing import get_tracer
from ..evaluation.ragas_eval import RagasEvaluator
from .reranker import CrossEncoderReranker

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
        self.reranker = CrossEncoderReranker()
        
    async def _expand_query(self, query: str, llm_provider: str) -> str:
        try:
            chat_messages = [
                {"role": "system", "content": "You are a query expansion assistant. Reply with 2-3 search keywords or synonyms for the user's question, separated by spaces. Do not write full sentences or explanations."},
                {"role": "user", "content": query}
            ]
            import openai
            import os
            
            if llm_provider == "groq":
                groq_key = os.getenv("GROQ_API_KEY")
                groq_model = os.getenv("LLM_MODEL", "groq/compound-mini")
                if groq_key:
                    client = openai.AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
                    completion = await client.chat.completions.create(
                        model=groq_model,
                        messages=chat_messages,
                        max_tokens=20
                    )
                    return completion.choices[0].message.content or ""
            elif llm_provider == "openai":
                openai_key = os.getenv("OPENAI_API_KEY")
                openai_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
                if openai_key:
                    client = openai.AsyncOpenAI(api_key=openai_key)
                    completion = await client.chat.completions.create(
                        model=openai_model,
                        messages=chat_messages,
                        max_tokens=20
                    )
                    return completion.choices[0].message.content or ""
        except Exception:
            pass
        return ""

    async def chat(self, tenant_id: str, message: str, conversation_id: Optional[str] = None, collection_id: Optional[str] = None, access_groups: Optional[List[str]] = None) -> ChatResponse:
        start_time = time.time()
        import os
        llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
        
        with tracer.start_as_current_span("chat_session") as span:
            span.set_attribute("tenant_id", tenant_id)
            
            # 1. Get or create conversation
            conv_id = await self.memory.get_or_create_conversation(tenant_id, conversation_id)
            
            # 2. Add user message to history
            await self.memory.add_message(conv_id, "user", message)
            
            # Query Expansion (Optional)
            search_query = message
            if os.getenv("QUERY_EXPANSION", "false").lower() == "true" and llm_provider != "mock":
                try:
                    expanded_query = await self._expand_query(message, llm_provider)
                    if expanded_query:
                        search_query = f"{message} {expanded_query}"
                        logger.info("Query expanded successfully", original=message, expanded=search_query)
                except Exception as e:
                    logger.error("Failed to expand query", error=str(e))
            
            # 3. Retrieve relevant chunks
            # We fetch top 50, then rerank down to top 5
            chunks = await self.query_engine.hybrid_search(
                tenant_id=tenant_id,
                query_text=search_query,
                top_k=50,
                collection_id=collection_id,
                access_groups=access_groups
            )
            
            # 4. Rerank using CrossEncoder
            # Convert retrieved chunks into dictionaries for the reranker
            dict_chunks = [{"payload": {"content": c.content}, "chunk": c} for c in chunks]
            reranked = self.reranker.rerank(query=message, results=dict_chunks, top_k=10)
            # Reconstruct chunks from reranked output
            chunks = [r["chunk"] for r in reranked]
            
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
            
            # Hostile-Witness System Prompt
            system_prompt = (
                "You are an expert Legal and Medical Assessor. You must answer questions strictly based on the provided context.\n"
                "HOSTILE WITNESS PROTOCOL:\n"
                "- Do NOT use external knowledge, assume, or extrapolate.\n"
                "- If the provided context does not explicitly state the answer, you MUST reply: \"UNABLE TO VERIFY: I could not find sufficient information in the provided context to answer your question.\"\n"
                "- Cite sources explicitly as [Source: <doc_id>, p.<page_num>]."
            )
            
            # Check for compliance_tier=STRICT and unverified_structures
            requires_strict_disclaimer = any(c.compliance_tier == "strict" for c in chunks)
            unverified_issues = set()
            for c in chunks:
                if c.unverified_structures:
                    unverified_issues.update(c.unverified_structures)
                    
            if requires_strict_disclaimer:
                system_prompt += "\n- COMPLIANCE TIER STRICT: The documents queried are under strict compliance. Ensure maximum fidelity."
            
            user_content = f"Context:\n{context_str}\n\nQuestion: {message}"
            
            # Fetch past history for multi-turn reasoning
            past_messages = await self.memory.get_history(conv_id, limit=6)
            
            chat_messages = [{"role": "system", "content": system_prompt}]
            
            for past_msg in past_messages:
                # Add historical messages (skip system/context, just raw Q&A)
                chat_messages.append({"role": past_msg["role"], "content": past_msg["content"]})
                
            chat_messages.append({"role": "user", "content": user_content})

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
            elif llm_provider == "groq":
                try:
                    groq_key = os.getenv("GROQ_API_KEY")
                    groq_model = os.getenv("LLM_MODEL", "groq/compound-mini")
                    if groq_key:
                        client = openai.AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
                        completion = await client.chat.completions.create(
                            model=groq_model,
                            messages=chat_messages
                        )
                        generated_content = completion.choices[0].message.content
                        model_used = f"groq-{groq_model}"
                    else:
                        logger.error("Groq API key not configured")
                except Exception as e:
                    logger.error("Failed to generate answer with Groq", error=str(e))

            if not generated_content:
                answer_parts = [f"Based on the documents (Mock Mode, set LLM_PROVIDER & API key to enable real generation), here is what I found regarding '{message}':\n"]
                if not chunks:
                    answer_parts.append("I could not find any relevant information in the uploaded documents.")
                else:
                    for cit in citations:
                        page_ref = f"p.{cit.page_numbers[0]}" if cit.page_numbers else "unknown page"
                        answer_parts.append(f"• {cit.content_snippet} [Source: {cit.document_id}, {page_ref}]\n")
                generated_content = "\n".join(answer_parts)
                
            # Append legal disclaimer if unverified structures were used in generation
            if unverified_issues:
                disclaimer = "\n\n*** LEGAL DISCLAIMER ***\nThis answer was derived from documents containing unverified or malformed structures: "
                disclaimer += ", ".join(unverified_issues)
                disclaimer += ". Please verify the original source document."
                generated_content += disclaimer
            
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
                evaluator = RagasEvaluator()
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
