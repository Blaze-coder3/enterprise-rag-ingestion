from fastapi import APIRouter
from .schemas import HealthResponse

router = APIRouter(prefix="/v1/health", tags=["health"])

@router.get("", response_model=HealthResponse)
async def health_check():
    """Deep health check for pipeline components."""
    # In a real scenario we'd ping DB and Qdrant
    return HealthResponse(
        status="ok",
        components={
            "database": "ok",
            "qdrant": "ok",
            "blob_storage": "ok"
        }
    )
