from contextlib import asynccontextmanager
from fastapi import FastAPI
from .config import settings
from .observability.logging import setup_logging, get_logger
from .observability.tracing import setup_tracing
from .api import routes_ingest, routes_documents, routes_health, routes_query, routes_chat
from .api.dependencies import get_container

setup_logging(settings.log_level)
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize container and all its components
    container = get_container()
    
    logger.info("Initializing metadata store...")
    await container.metadata_store.initialize()
    
    logger.info("Initializing vector store...")
    await container.vector_store.initialize()
    
    logger.info("Starting worker pool...")
    await container.worker_pool.start()
    
    yield
    
    logger.info("Stopping worker pool...")
    await container.worker_pool.stop()

app = FastAPI(
    title="Enterprise RAG Ingestion Pipeline",
    description="Scalable, asynchronous document ingestion for RAG",
    version="0.1.0",
    lifespan=lifespan
)

# Setup OpenTelemetry tracing
setup_tracing(app, service_name="rag-pipeline-api")

# Include routes
app.include_router(routes_ingest.router)
app.include_router(routes_documents.router)
app.include_router(routes_health.router)
app.include_router(routes_query.router)
app.include_router(routes_chat.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.rag_pipeline.main:app", host="0.0.0.0", port=settings.port, reload=True)
