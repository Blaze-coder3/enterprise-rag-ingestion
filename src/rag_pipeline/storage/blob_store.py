import os
import aiofiles
from typing import Optional

class BlobStore:
    """Local filesystem blob store for raw documents."""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        
    def _get_tenant_path(self, tenant_id: str) -> str:
        tenant_path = os.path.join(self.base_path, tenant_id)
        os.makedirs(tenant_path, exist_ok=True)
        return tenant_path
        
    async def save_document(self, tenant_id: str, document_id: str, version_id: str, 
                            file_bytes: bytes, filename: str) -> str:
        """Saves a document and returns its path."""
        tenant_path = self._get_tenant_path(tenant_id)
        _, ext = os.path.splitext(filename)
        
        # Format: {document_id}_{version_id}{ext}
        safe_filename = f"{document_id}_{version_id}{ext}"
        full_path = os.path.join(tenant_path, safe_filename)
        
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(file_bytes)
            
        return full_path
        
    async def read_document(self, tenant_id: str, document_id: str, version_id: str, filename: str) -> Optional[bytes]:
        """Reads a document from storage."""
        tenant_path = self._get_tenant_path(tenant_id)
        _, ext = os.path.splitext(filename)
        safe_filename = f"{document_id}_{version_id}{ext}"
        full_path = os.path.join(tenant_path, safe_filename)
        
        if not os.path.exists(full_path):
            return None
            
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()
