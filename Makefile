.PHONY: help up down migrate seed test lint format clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Start all services (docker-compose)
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services are up! API: http://localhost:8000, Web: http://localhost:3000"

down: ## Stop all services
	docker-compose down

migrate: ## Run database migrations
	cd apps/api && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	cd apps/api && alembic revision --autogenerate -m "$(MSG)"

seed: ## Load sample data
	python scripts/seed_data.py

test: ## Run all tests
	pytest tests/ -v --cov=apps --cov=packages

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-e2e: ## Run e2e tests
	pytest tests/e2e/ -v

lint: ## Run linters
	ruff check apps/ packages/
	mypy apps/ packages/

format: ## Format code
	ruff format apps/ packages/
	black apps/ packages/

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/

install: ## Install all dependencies
	pip install -r requirements.txt
	cd apps/web && npm install

dev-api: ## Run API in development mode
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Run web in development mode
	cd apps/web && npm run dev

dev-workers: ## Run background workers
	cd apps/workers && python -m rq worker --url redis://localhost:6379

backfill: ## Run backfill for last 10 years
	python scripts/backfill.py --years 10

backfill-sp500: ## Run backfill for S&P 500 companies only
	python scripts/backfill.py --sp500 --years 10

logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show API logs
	docker-compose logs -f api

logs-workers: ## Show worker logs
	docker-compose logs -f workers

psql: ## Connect to Postgres
	docker-compose exec db psql -U aihedge -d aihedge

redis-cli: ## Connect to Redis
	docker-compose exec redis redis-cli

build: ## Build all Docker images
	docker-compose build

deploy-staging: ## Deploy to staging
	@echo "Deploying to staging..."
	./scripts/deploy.sh staging

deploy-prod: ## Deploy to production (requires confirmation)
	@echo "Are you sure you want to deploy to production? [y/N] " && read ans && [ $${ans:-N} = y ]
	./scripts/deploy.sh production
