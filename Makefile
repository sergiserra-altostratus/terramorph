.PHONY: up down build clean logs cli help

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start Terramorph (development mode)
	docker compose up --build -d
	@echo ""
	@echo "✓ Terramorph is running:"
	@echo "  Frontend → http://localhost:$${FRONTEND_PORT:-3000}"
	@echo "  Backend  → http://localhost:$${BACKEND_PORT:-8001}/docs"
	@echo ""

down: ## Stop Terramorph
	docker compose down

prod: ## Start in production mode
	DOCKER_TARGET=production TERRAMORPH_ENV=production TERRAMORPH_LOG_LEVEL=info docker compose up --build -d

logs: ## View logs (all services)
	docker compose logs -f

logs-backend: ## View backend logs only
	docker compose logs -f backend

logs-frontend: ## View frontend logs only
	docker compose logs -f frontend

restart: ## Restart all services
	docker compose restart

build: ## Build without starting
	docker compose build

clean: ## Stop and remove all containers, volumes, images
	docker compose down -v --rmi local
	@echo "✓ Cleaned up"

cli: ## Build CLI binary (requires Rust toolchain)
	cd cli && cargo build --release
	@echo "✓ CLI built at ./cli/target/release/terramorph"

test: ## Run backend tests
	cd backend && pip install -r requirements.txt -q && pytest tests/ -v

lint: ## Lint backend code
	cd backend && ruff check app/
