.PHONY: db db-stop db-down db-reset migrate migrate-new migrate-down seed seed-github refresh eval api frontend mlx-server test test-unit test-integration lint format typecheck install help

# ─── Infrastructure ───────────────────────────────────────────────────────────

db:
	docker compose up -d postgres neo4j
	@echo "Waiting for databases to be healthy..."
	@docker compose wait postgres neo4j 2>/dev/null || sleep 10  # requires Docker Compose v2.21+
	@echo "Databases ready."

db-stop:
	docker compose down

db-down: db-stop

db-reset:
	docker compose down -v
	$(MAKE) db
	$(MAKE) migrate

# ─── Database migrations ──────────────────────────────────────────────────────

migrate:
	uv run alembic upgrade head

migrate-new:
	@read -p "Migration name: " name; uv run alembic revision --autogenerate -m "$$name"

migrate-down:
	uv run alembic downgrade -1

# ─── Application ─────────────────────────────────────────────────────────────

api:
	uv run uvicorn talent_graph.api.main:create_app --factory --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && bun run dev

mlx-server:
	mlx_lm.server --model mlx-community/Qwen3.5-35B-A3B-4bit --port 8080

# ─── Data ─────────────────────────────────────────────────────────────────────

seed:
	uv run python -m talent_graph.scripts.seed_ingest --source all --query "multimodal dialogue"

seed-github:
	uv run python -m talent_graph.scripts.seed_ingest --source github

refresh:
	uv run python -m talent_graph.scripts.seed_ingest --source all --query "multimodal dialogue"

eval:
	uv run python -m talent_graph.scripts.evaluate

# ─── Quality ──────────────────────────────────────────────────────────────────

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/ alembic/
	uv run ruff check --fix src/ tests/

typecheck:
	uv run mypy src/

# ─── Setup ────────────────────────────────────────────────────────────────────

install:
	uv sync --extra dev

help:
	@echo "Available targets:"
	@echo "  make db            - Start Postgres + Neo4j via Docker Compose"
	@echo "  make db-stop       - Stop databases (alias: db-down)"
	@echo "  make db-reset      - Reset databases (destructive)"
	@echo "  make migrate       - Run Alembic migrations"
	@echo "  make seed          - Ingest sample data (OpenAlex + GitHub)"
	@echo "  make refresh       - Re-run ingestion to pick up new data"
	@echo "  make eval          - Run offline evaluation (precision@k, MRR)"
	@echo "  make api           - Start FastAPI dev server (port 8000)"
	@echo "  make frontend      - Start Next.js dev server (port 3000)"
	@echo "  make mlx-server    - Start MLX LLM server (port 8080)"
	@echo "  make test          - Run all tests"
	@echo "  make lint          - Run ruff linter"
	@echo "  make format        - Format code with ruff"
