# =============================================================================
# Fuel Router - Developer & Operations Makefile
# =============================================================================

# Static variables and compose flags
DOCKER_COMPOSE_BASE := -f docker-compose.base.yml
ENV_DEV_FLAG := $(if $(wildcard .env.dev),--env-file .env.dev,)
ENV_PROD_FLAG := $(if $(wildcard .env.prod),--env-file .env.prod,)

COMPOSE_DEV := docker compose $(DOCKER_COMPOSE_BASE) -f docker-compose.dev.yml $(ENV_DEV_FLAG)
COMPOSE_PROD := docker compose -f docker-compose.prod.yml $(ENV_PROD_FLAG)

STATIONS_CSV ?= dataset/fuel-prices-for-be-assessment.csv
LOAD_STATIONS_FLAGS ?=
TEST_ARGS ?=

.PHONY: help setup-env up down build logs restart restart-backend \
        dev-up dev-down dev-build dev-logs dev-restart \
        migrate load-data test lint shell \
        prod-build prod-up prod-down prod-logs prod-migrate prod-restart-backend

# -----------------------------------------------------------------------------
# Help & Information
# -----------------------------------------------------------------------------
help:
	@echo "Available Makefile commands:"
	@echo "  make setup-env     - Initialize .env.dev and .env.prod from .env.example"
	@echo "  make up            - Start development environment (with automatic setup-env)"
	@echo "  make down          - Stop development environment"
	@echo "  make build         - Build development Docker images"
	@echo "  make logs          - Follow development backend logs"
	@echo "  make restart-backend - Restart development backend container (alias: make restart)"
	@echo "  make migrate       - Run database migrations in development"
	@echo "  make load-data     - Import, deduplicate, and geocode station dataset"
	@echo "  make test          - Run test suite inside backend container (optional: TEST_ARGS='...')"
	@echo "  make lint          - Run ruff and mypy linters inside backend container"
	@echo "  make shell         - Open interactive Django shell inside backend container"
	@echo "  make prod-build    - Build production multi-stage images"
	@echo "  make prod-up       - Start production stack with Nginx reverse proxy"
	@echo "  make prod-down     - Stop production stack"
	@echo "  make prod-logs     - Follow production stack logs"
	@echo "  make prod-migrate  - Run database migrations in production"
	@echo "  make prod-restart-backend - Restart production backend container"

# -----------------------------------------------------------------------------
# Environment Initialization
# -----------------------------------------------------------------------------
setup-env:
	@docker network create dokploy-network >/dev/null 2>&1 || true
	@if [ ! -f .env.dev ]; then \
		cp .env.example .env.dev; \
		echo "Initialized .env.dev from .env.example"; \
	else \
		echo ".env.dev already exists."; \
	fi
	@if [ ! -f .env.prod ]; then \
		cp .env.example .env.prod; \
		echo "Initialized .env.prod from .env.example"; \
	else \
		echo ".env.prod already exists."; \
	fi

# -----------------------------------------------------------------------------
# Development Environment (Default Shortcuts)
# -----------------------------------------------------------------------------
up: setup-env dev-up
down: dev-down
build: dev-build
logs: dev-logs
restart: restart-backend
restart-backend:
	$(COMPOSE_DEV) restart backend

dev-up:
	$(COMPOSE_DEV) up -d

dev-down:
	$(COMPOSE_DEV) down

dev-build:
	$(COMPOSE_DEV) build

dev-logs:
	$(COMPOSE_DEV) logs -f backend

dev-restart: restart-backend

migrate:
	$(COMPOSE_DEV) exec -T backend python manage.py migrate

load-data:
	$(COMPOSE_DEV) exec -T backend python manage.py import_stations $(STATIONS_CSV)
	$(COMPOSE_DEV) exec -T backend python manage.py load_stations $(LOAD_STATIONS_FLAGS)
	$(COMPOSE_DEV) exec -T backend python manage.py geocode_stations

test:
	$(COMPOSE_DEV) exec -T backend pytest $(TEST_ARGS)

lint:
	$(COMPOSE_DEV) exec -T backend ruff check .
	$(COMPOSE_DEV) exec -T backend mypy .

shell:
	$(COMPOSE_DEV) exec backend python manage.py shell

# -----------------------------------------------------------------------------
# Production Environment
# -----------------------------------------------------------------------------
prod-build:
	$(COMPOSE_PROD) build

prod-up: setup-env
	$(COMPOSE_PROD) up -d

prod-down:
	$(COMPOSE_PROD) down

prod-logs:
	$(COMPOSE_PROD) logs -f

prod-migrate:
	$(COMPOSE_PROD) exec -T backend python manage.py migrate

prod-restart-backend:
	$(COMPOSE_PROD) restart backend

