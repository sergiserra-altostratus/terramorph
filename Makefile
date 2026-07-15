.PHONY: dev prod build-cli clean lint-backend lint-frontend test-backend test-frontend help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start development environment with hot-reload
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

prod: ## Start production environment
	docker compose up --build -d

build-cli: ## Build CLI binary (requires Rust toolchain)
	cd cli && cargo build --release

clean: ## Stop containers and clean build artifacts
	docker compose down -v
	cd cli && cargo clean 2>/dev/null || true

lint-backend: ## Run backend linter
	cd backend && ruff check app/

lint-frontend: ## Run frontend linter
	cd frontend && npm run lint

test-backend: ## Run backend tests
	cd backend && pytest tests/ -v

test-frontend: ## Run frontend tests
	cd frontend && npm test

install-backend: ## Install backend dependencies locally
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies locally
	cd frontend && npm install
