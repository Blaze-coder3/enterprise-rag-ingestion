import abc
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass

@dataclass
class SourceDocument:
    """Represents a document retrieved from a source connector."""
    filename: str
    file_bytes: bytes
    metadata: Dict[str, Any]
    document_type: Optional[str] = None
    tags: list[str] = None

class BaseSourceConnector(abc.ABC):
    """
    Abstract protocol for fetching raw documents into the ingestion pipeline.
    This abstraction allows the pipeline to decouple from the HTTP API.
    """
    
    @abc.abstractmethod
    async def fetch(self, uri: str, **kwargs) -> SourceDocument:
        """Fetches a single document."""
        pass
        
    @abc.abstractmethod
    async def poll(self, **kwargs) -> AsyncGenerator[SourceDocument, None]:
        """Continuously yields documents from a streaming source or queue."""
        pass

class LocalUploadConnector(BaseSourceConnector):
    """
    Stub for the existing FastAPI endpoint where files are directly uploaded.
    In a real system, the API route would pass the upload to this connector.
    """
    async def fetch(self, uri: str, **kwargs) -> SourceDocument:
        # In this stub, uri would be the local file path
        import aiofiles
        async with aiofiles.open(uri, 'rb') as f:
            file_bytes = await f.read()
            
        import os
        return SourceDocument(
            filename=os.path.basename(uri),
            file_bytes=file_bytes,
            metadata=kwargs.get("metadata", {}),
            document_type=kwargs.get("document_type"),
            tags=kwargs.get("tags", [])
        )
        
    async def poll(self, **kwargs) -> AsyncGenerator[SourceDocument, None]:
        # Uploads are event-driven, not polled
        yield # type: ignore
        
class S3Connector(BaseSourceConnector):
    """
    Stub for an enterprise S3/Blob storage connector.
    Demonstrates how we could easily hook up an S3 bucket watcher to the ingest service.
    """
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region
        
    async def fetch(self, uri: str, **kwargs) -> SourceDocument:
        raise NotImplementedError("S3 integration requires boto3/aioboto3")
        
    async def poll(self, **kwargs) -> AsyncGenerator[SourceDocument, None]:
        raise NotImplementedError("S3 integration requires boto3/aioboto3")
