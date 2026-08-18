import asyncio
import traceback
from typing import Dict, Any
from ..observability.logging import get_logger
from ..core.models import DocumentStatus

logger = get_logger("pipeline_worker")

class IngestionJob:
    def __init__(self, document_id: str, version_id: str, tenant_id: str, filename: str):
        self.document_id = document_id
        self.version_id = version_id
        self.tenant_id = tenant_id
        self.filename = filename
        self.attempts = 0

class WorkerPool:
    """Async worker pool for processing ingestion jobs."""
    
    def __init__(self, pipeline_orchestrator, num_workers: int = 4):
        self.queue = asyncio.Queue()
        self.workers = []
        self.pipeline = pipeline_orchestrator
        self.num_workers = num_workers
        self.is_running = False
        
    async def start(self):
        self.is_running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
        logger.info(f"Started worker pool with {self.num_workers} workers.")
            
    async def stop(self):
        self.is_running = False
        for _ in range(self.num_workers):
            await self.queue.put(None)
        await asyncio.gather(*self.workers)
        logger.info("Worker pool stopped.")
        
    async def submit_job(self, document_id: str, version_id: str, tenant_id: str, filename: str):
        job = IngestionJob(document_id, version_id, tenant_id, filename)
        await self.queue.put(job)
        logger.info("Job submitted to queue", document_id=document_id)
        
    async def _worker_loop(self, worker_id: int):
        while self.is_running:
            job = await self.queue.get()
            if job is None:
                self.queue.task_done()
                break
                
            logger.info("Worker starting job", worker_id=worker_id, document_id=job.document_id)
            
            try:
                # We acquire the tenant semaphore before starting pipeline work
                # This ensures we don't start the job until fairness constraints are met
                await self.pipeline.tenant_scheduler.acquire(job.tenant_id)
                
                try:
                    await self.pipeline.process_document(
                        tenant_id=job.tenant_id,
                        document_id=job.document_id,
                        version_id=job.version_id,
                        filename=job.filename
                    )
                finally:
                    self.pipeline.tenant_scheduler.release(job.tenant_id)
                    
            except Exception as e:
                job.attempts += 1
                logger.error("Job failed", error=str(e), document_id=job.document_id, attempts=job.attempts, exc_info=True)
                
                # Simple retry policy
                if job.attempts < 3:
                    # Exponential backoff
                    await asyncio.sleep(2 ** job.attempts)
                    await self.queue.put(job)
                else:
                    logger.error("Job permanently failed after retries", document_id=job.document_id)
                    # Mark as permanently failed in state machine
                    await self.pipeline.state_manager.transition(
                        document_id=job.document_id, 
                        version_id=job.version_id,
                        new_status=DocumentStatus.PERMANENT_FAILURE
                    )
                    
            self.queue.task_done()
