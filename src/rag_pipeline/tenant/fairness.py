import asyncio
import time
from typing import Dict
from ..observability.metrics import tenant_queue_depth, tenant_active_jobs, tenant_wait_seconds

class TenantFairScheduler:
    """Ensures no single tenant can starve others by consuming all workers."""
    
    def __init__(self, default_concurrency: int = 5):
        self.default_concurrency = default_concurrency
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        
    def _get_semaphore(self, tenant_id: str) -> asyncio.Semaphore:
        if tenant_id not in self._semaphores:
            # In a real system, we'd fetch the tenant's specific limit from DB
            self._semaphores[tenant_id] = asyncio.Semaphore(self.default_concurrency)
        return self._semaphores[tenant_id]
        
    async def acquire(self, tenant_id: str) -> None:
        """Blocks until the tenant has an available concurrency slot."""
        tenant_queue_depth.labels(tenant_id=tenant_id).inc()
        
        start_time = time.time()
        sem = self._get_semaphore(tenant_id)
        
        await sem.acquire()
        
        # We got the slot
        wait_time = time.time() - start_time
        tenant_wait_seconds.labels(tenant_id=tenant_id).observe(wait_time)
        tenant_queue_depth.labels(tenant_id=tenant_id).dec()
        tenant_active_jobs.labels(tenant_id=tenant_id).inc()
        
    def release(self, tenant_id: str) -> None:
        """Releases a concurrency slot back to the tenant."""
        sem = self._get_semaphore(tenant_id)
        sem.release()
        tenant_active_jobs.labels(tenant_id=tenant_id).dec()
