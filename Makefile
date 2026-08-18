.PHONY: install dev test docker-up docker-down clean demo

install:
	pip install -e ".[dev]"

dev:
	uvicorn src.rag_pipeline.main:app --reload --port 8000

test:
	pytest tests/ -v

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache
	rm -rf src/rag_pipeline/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf data/*.db

demo:
	docker compose up -d
	@echo "Waiting for services..."
	sleep 15
	python scripts/seed_demo.py
	@echo ""
	@echo "=== RAG Pipeline Running ==="
	@echo "Streamlit UI:    http://localhost:8501"
	@echo "FastAPI Docs:    http://localhost:8000/docs"
	@echo "Jaeger Traces:   http://localhost:16686"
	@echo "Grafana:         http://localhost:3000  (admin/admin)"
	@echo "Qdrant:          http://localhost:6333/dashboard"
