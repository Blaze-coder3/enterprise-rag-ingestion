import os
import aiofiles
from pathlib import Path
from ..config import settings

class BlobStore:
    """Simple local storage client for raw object storage."""
    
    def __init__(self, base_dir: str = settings.blob_storage_path):
        self.base_dir = Path(base_dir)
        
    async def save_document(self, tenant_id: str, document_id: str, version_id: str, file_bytes: bytes, filename: str) -> str:
        """Saves raw file bytes to disk and returns the relative storage path."""
        ext = Path(filename).suffix
        if not ext:
            ext = ".bin"
            
        rel_path = f"raw/{tenant_id}/{document_id}/{version_id}/original{ext}"
        full_path = self.base_dir / rel_path
        
        # Ensure directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(file_bytes)
            
        return rel_path

    async def read_document(self, tenant_id: str, document_id: str, version_id: str, filename: str) -> bytes:
        """Reads raw file bytes from disk."""
        ext = Path(filename).suffix
        if not ext:
            ext = ".bin"
            
        rel_path = f"raw/{tenant_id}/{document_id}/{version_id}/original{ext}"
        full_path = self.base_dir / rel_path
        
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()
