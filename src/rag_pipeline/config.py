from dotenv import load_dotenv
load_dotenv()

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Settings
    port: int = 8000
    environment: str = "development"
    log_level: str = "info"

    # Qdrant Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # Storage
    database_url: str = "sqlite:///data/pipeline.db"
    blob_storage_path: str = "./data/blobs"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    sparse_embedding_model: str = "Qdrant/bm25"

    # Observability
    jaeger_endpoint: str = "localhost:4317"

    # External Integrations (Optional)
    azure_di_endpoint: str | None = None
    azure_di_key: str | None = None
    llm_provider: str = "mock"
    llm_model: str = "phi3"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
