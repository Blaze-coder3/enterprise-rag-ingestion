import time
from typing import Dict, Any, Type
import asyncio
from ..observability.logging import get_logger
from ..observability.tracing import get_tracer
from ..observability.metrics import stage_duration_seconds, docs_processing
from ..core.models import DocumentStatus, QualityVerdict
from ..core.exceptions import RagPipelineError
from ..core.decisions import DecisionEvent

logger = get_logger("pipeline_orchestrator")
tracer = get_tracer("rag_pipeline")

class PipelineOrchestrator:
    """Orchestrates the execution of pipeline stages."""
    
    def __init__(self, 
                 state_manager, 
                 metadata_store, 
                 blob_store, 
                 parser_router,
                 normalizer,
                 chunker,
                 embedder,
                 vector_store,
                 tenant_scheduler):
                 
        self.state_manager = state_manager
        self.metadata_store = metadata_store
        self.blob_store = blob_store
        self.parser_router = parser_router
        self.normalizer = normalizer
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.tenant_scheduler = tenant_scheduler
        
    async def process_document(self, tenant_id: str, document_id: str, version_id: str, filename: str) -> None:
        """Executes the pipeline stages for a document."""
        docs_processing.labels(tenant_id=tenant_id).inc()
        
        try:
            with tracer.start_as_current_span(f"process_document") as span:
                span.set_attribute("tenant_id", tenant_id)
                span.set_attribute("document_id", document_id)
                
                logger.info("Starting pipeline", document_id=document_id, tenant_id=tenant_id)
                
                # Fetch raw file from blob storage
                file_bytes = await self.blob_store.read_document(tenant_id, document_id, version_id, filename)
                if not file_bytes:
                    raise RagPipelineError("Document not found in blob storage")
                    
                # 1. PARSING
                await self.state_manager.transition(document_id, version_id, DocumentStatus.PARSING)
                with tracer.start_as_current_span("stage.parse") as parse_span:
                    start_time = time.time()
                    
                    parser, decision_signals = self.parser_router.select_parser(filename, file_bytes)
                    
                    # Log decision
                    await self.metadata_store.log_decision(DecisionEvent(
                        trace_id=str(parse_span.get_span_context().trace_id),
                        document_id=document_id,
                        tenant_id=tenant_id,
                        stage="parser_selection",
                        decision=decision_signals["decision"],
                        reason=decision_signals["reason"],
                        policy_version="v1",
                        input_signals=decision_signals["signals"]
                    ))
                    
                    parse_result = await parser.parse(file_bytes, filename, {})
                    
                    stage_duration_seconds.labels(stage="parse", tenant_id=tenant_id).observe(time.time() - start_time)

                # 2. QUALITY CHECK
                await self.state_manager.transition(document_id, version_id, DocumentStatus.QUALITY_CHECK)
                with tracer.start_as_current_span("stage.quality_gate") as qg_span:
                    verdict, metrics, reason = self.parser_router.quality_gate(parse_result, parser.name)
                    
                    # Log decision
                    await self.metadata_store.log_decision(DecisionEvent(
                        trace_id=str(qg_span.get_span_context().trace_id),
                        document_id=document_id,
                        tenant_id=tenant_id,
                        stage="quality_gate",
                        decision=verdict.value,
                        reason=reason,
                        policy_version="v1",
                        input_signals=metrics.model_dump()
                    ))
                    
                    if verdict == QualityVerdict.NEEDS_REVIEW:
                        await self.state_manager.transition(document_id, version_id, DocumentStatus.NEEDS_REVIEW)
                        logger.warn("Document needs review due to poor quality parse", document_id=document_id)
                        return
                    elif verdict == QualityVerdict.FALLBACK:
                        # Simple fallback demo, would ideally recurse or retry
                        logger.info("Falling back to ADI parser", document_id=document_id)
                        parser = self.parser_router.adi
                        parse_result = await parser.parse(file_bytes, filename, {})

                doc_record = await self.metadata_store.get_document(tenant_id, document_id)
                collection_id = doc_record.collection_id if doc_record and hasattr(doc_record, "collection_id") else "default"

                # 3. NORMALIZATION
                await self.state_manager.transition(document_id, version_id, DocumentStatus.NORMALIZED)
                await asyncio.sleep(0.3)
                with tracer.start_as_current_span("stage.normalize"):
                    start_time = time.time()
                    canonical_doc = self.normalizer.normalize(
                        document_id=document_id,
                        tenant_id=tenant_id,
                        version_id=version_id,
                        title=filename,
                        parse_result=parse_result,
                        parser_name=parser.name,
                        parser_version=parser.version,
                        quality_metrics=metrics,
                        collection_id=collection_id
                    )
                    stage_duration_seconds.labels(stage="normalize", tenant_id=tenant_id).observe(time.time() - start_time)

                # 4. CHUNKING
                await self.state_manager.transition(document_id, version_id, DocumentStatus.CHUNKING)
                await asyncio.sleep(0.3)
                with tracer.start_as_current_span("stage.chunk"):
                    start_time = time.time()
                    from ..chunking.base import ChunkConfig
                    config = ChunkConfig()
                    chunks = self.chunker.chunk(canonical_doc, config)
                    stage_duration_seconds.labels(stage="chunk", tenant_id=tenant_id).observe(time.time() - start_time)

                # 5. EMBEDDING
                await self.state_manager.transition(document_id, version_id, DocumentStatus.EMBEDDING)
                await asyncio.sleep(0.3)
                with tracer.start_as_current_span("stage.embed"):
                    start_time = time.time()
                    await self.embedder.embed_batch(chunks)
                    stage_duration_seconds.labels(stage="embed", tenant_id=tenant_id).observe(time.time() - start_time)

                # 6. INDEXING
                await self.state_manager.transition(document_id, version_id, DocumentStatus.INDEXING)
                await asyncio.sleep(0.3)
                with tracer.start_as_current_span("stage.index"):
                    start_time = time.time()
                    await self.vector_store.upsert_chunks(chunks)
                    stage_duration_seconds.labels(stage="index", tenant_id=tenant_id).observe(time.time() - start_time)

                # DONE
                await self.state_manager.transition(document_id, version_id, DocumentStatus.READY)
                await asyncio.sleep(0.3)
                logger.info("Pipeline completed successfully", document_id=document_id)
                
        except Exception as e:
            logger.error("Pipeline failed", error=str(e), document_id=document_id, exc_info=True)
            raise
        finally:
            docs_processing.labels(tenant_id=tenant_id).dec()
