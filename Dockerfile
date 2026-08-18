FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 --extra-index-url https://download.pytorch.org/whl/cpu -e .

# Create data directories
RUN mkdir -p /app/data/blobs

# Expose port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "src.rag_pipeline.main:app", "--host", "0.0.0.0", "--port", "8000"]
