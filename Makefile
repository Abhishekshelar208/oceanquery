# OceanQuery Development Automation
.PHONY: help install dev front backend db-up db-down db-reset test lint fmt clean

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)OceanQuery Development Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m%-20s\033[0m %s\n", "Command", "Description"} /^[a-zA-Z_-]+:.*?##/ { printf "\033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Installation

install: ## Install all dependencies (frontend + backend)
	@echo "$(BLUE)Installing OceanQuery dependencies...$(NC)"
	@echo "$(YELLOW)Installing Flutter dependencies...$(NC)"
	cd frontend && flutter pub get
	@echo "$(YELLOW)Setting up Python virtual environment...$(NC)"
	cd backend && python3 -m venv .venv --upgrade-deps
	@echo "$(YELLOW)Installing Python dependencies...$(NC)"
	cd backend && source .venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)✅ Installation complete!$(NC)"

install-frontend: ## Install only frontend dependencies
	@echo "$(YELLOW)Installing Flutter dependencies...$(NC)"
	cd frontend && flutter pub get

install-backend: ## Install only backend dependencies
	@echo "$(YELLOW)Setting up Python virtual environment...$(NC)"
	cd backend && python3 -m venv .venv --upgrade-deps
	@echo "$(YELLOW)Installing Python dependencies...$(NC)"
	cd backend && source .venv/bin/activate && pip install -r requirements.txt

##@ Development

dev: db-up backend ## Start full development environment (database + backend)

backend: ## Start backend development server
	@echo "$(BLUE)Starting OceanQuery backend server...$(NC)"
	cd backend && source .venv/bin/activate && python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

front: ## Start frontend development server
	@echo "$(BLUE)Starting Flutter web development server...$(NC)"
	cd frontend && flutter run -d chrome --web-renderer canvaskit --web-port 8080

frontend: front ## Alias for 'front'

##@ Database

db-up: ## Start PostgreSQL database
	@echo "$(BLUE)Starting PostgreSQL database...$(NC)"
	cd infra && docker compose up -d postgres
	@echo "$(GREEN)✅ Database started on port 5432$(NC)"
	@echo "$(YELLOW)Waiting for database to be ready...$(NC)"
	@sleep 5
	@$(MAKE) db-init

db-down: ## Stop PostgreSQL database
	@echo "$(YELLOW)Stopping PostgreSQL database...$(NC)"
	cd infra && docker compose down
	@echo "$(GREEN)✅ Database stopped$(NC)"

db-reset: ## Reset database (drop and recreate tables)
	@echo "$(RED)⚠️  Resetting database (this will delete all data!)$(NC)"
	cd backend && source .venv/bin/activate && python -m src.db.init_db --reset
	@echo "$(GREEN)✅ Database reset complete$(NC)"

db-init: ## Initialize database tables
	@echo "$(BLUE)Initializing database...$(NC)"
	cd backend && source .venv/bin/activate && python -m src.db.init_db --create --sample
	@echo "$(GREEN)✅ Database initialized with sample data$(NC)"

db-check: ## Check database connection
	@echo "$(BLUE)Checking database connection...$(NC)"
	cd backend && source .venv/bin/activate && python -m src.db.init_db --check

db-stats: ## Show database statistics
	@echo "$(BLUE)Database Statistics:$(NC)"
	cd backend && source .venv/bin/activate && python -m src.db.init_db --stats

db-admin: ## Start PgAdmin (database admin interface)
	@echo "$(BLUE)Starting PgAdmin...$(NC)"
	cd infra && docker compose --profile admin up -d pgadmin
	@echo "$(GREEN)✅ PgAdmin started at http://localhost:8081$(NC)"
	@echo "$(YELLOW)Login: admin@oceanquery.com / admin123$(NC)"

##@ Data Ingestion

ingest-argo: ## Ingest ARGO data from directory
	@echo "$(BLUE)Starting ARGO data ingestion...$(NC)"
	cd backend && source .venv/bin/activate && python scripts/ingest_argo.py ingest

ingest-argo-sample: ## Ingest sample ARGO data (dry run)
	@echo "$(BLUE)Ingesting sample ARGO data...$(NC)"
	cd backend && source .venv/bin/activate && python scripts/ingest_argo.py ingest --sample --dry-run

ingest-stats: ## Get ingestion statistics
	@echo "$(BLUE)Getting ingestion statistics...$(NC)"
	cd backend && source .venv/bin/activate && python scripts/ingest_argo.py stats

ingest-optimize: ## Optimize database and cleanup logs
	@echo "$(BLUE)Optimizing database...$(NC)"
	cd backend && source .venv/bin/activate && python scripts/ingest_argo.py optimize

ingest-resume: ## Resume interrupted ingestion
	@echo "$(BLUE)Resuming ARGO ingestion...$(NC)"
	cd backend && source .venv/bin/activate && python scripts/ingest_argo.py resume

ingest-file: ## Ingest single file (usage: make ingest-file FILE=path/to/file.nc)
	@echo "$(BLUE)Ingesting single file...$(NC)"
	@if [ -z "$(FILE)" ]; then echo "Usage: make ingest-file FILE=path/to/file.nc"; exit 1; fi
	cd backend && source .venv/bin/activate && python scripts/ingest_argo.py ingest-file --input "$(FILE)"

##@ Code Quality

test: ## Run tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && flutter test

test-backend: ## Run only backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v

test-frontend: ## Run only frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && flutter test

lint: ## Run linting for all code
	@echo "$(BLUE)Linting backend code...$(NC)"
	cd backend && source .venv/bin/activate && flake8 src/ --max-line-length=88 --extend-ignore=E203
	@echo "$(BLUE)Linting frontend code...$(NC)"
	cd frontend && flutter analyze

lint-backend: ## Run backend linting only
	@echo "$(BLUE)Linting backend code...$(NC)"
	cd backend && source .venv/bin/activate && flake8 src/ --max-line-length=88 --extend-ignore=E203

lint-frontend: ## Run frontend linting only
	@echo "$(BLUE)Linting frontend code...$(NC)"
	cd frontend && flutter analyze

fmt: ## Format all code
	@echo "$(BLUE)Formatting backend code...$(NC)"
	cd backend && source .venv/bin/activate && black src/ && isort src/
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd frontend && dart format lib/

fmt-backend: ## Format backend code only
	@echo "$(BLUE)Formatting backend code...$(NC)"
	cd backend && source .venv/bin/activate && black src/ && isort src/

fmt-frontend: ## Format frontend code only
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd frontend && dart format lib/

##@ Docker

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker build -t oceanquery-backend backend/
	docker build -t oceanquery-frontend frontend/

docker-up: ## Start all services with Docker
	@echo "$(BLUE)Starting all services...$(NC)"
	cd infra && docker compose up -d

docker-down: ## Stop all Docker services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	cd infra && docker compose down

docker-logs: ## Show Docker logs
	cd infra && docker compose logs -f

##@ Utilities

clean: ## Clean build artifacts and caches
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	cd frontend && flutter clean
	cd backend && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	cd backend && find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Clean complete$(NC)"

logs-backend: ## Show backend logs
	cd backend && source .venv/bin/activate && tail -f logs/app.log 2>/dev/null || echo "No log file found"

status: ## Show development environment status
	@echo "$(BLUE)OceanQuery Development Status:$(NC)"
	@echo ""
	@echo "$(YELLOW)Frontend:$(NC)"
	@cd frontend && flutter --version | head -1 || echo "Flutter not installed"
	@echo ""
	@echo "$(YELLOW)Backend:$(NC)"
	@cd backend && source .venv/bin/activate && python --version 2>/dev/null || echo "Python venv not setup"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}" --filter "name=oceanquery" || echo "Docker not running"

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "$(YELLOW)API documentation available at: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)ReDoc documentation available at: http://localhost:8000/redoc$(NC)"

##@ Production

build: ## Build for production
	@echo "$(BLUE)Building for production...$(NC)"
	cd frontend && flutter build web
	@echo "$(GREEN)✅ Production build complete$(NC)"

deploy: ## Deploy to production (placeholder)
	@echo "$(RED)Production deployment not implemented yet$(NC)"

##@ Default

.DEFAULT_GOAL := help
