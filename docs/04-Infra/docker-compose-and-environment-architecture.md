# Docker Compose and Environment Architecture

## Overview

SpotterRouter uses Docker Compose to run its complete stack locally and in production. The system is split across multiple compose files to keep shared service configurations in one place while allowing development and production environments to override settings cleanly.

---

## The Three Compose Files

The setup uses three distinct Docker Compose files:

1. `docker-compose.base.yml`
   - Defines the shared architecture used by all environments.
   - Declares the core services: `backend`, `db` (PostgreSQL with PostGIS), `redis`, `worker` (Celery background worker), and `osrm` (Open Source Routing Machine).
   - Configures named volumes for database persistence (`postgres_data`) and routing data (`osrm_data`).
   - Connects all services to a shared bridge network named `spotter-network`.

2. `docker-compose.dev.yml`
   - Overlays settings specifically for local engineering.
   - Mounts the local repository source code into the running containers so code changes take effect immediately without rebuilding images.
   - Exposes container ports directly to `localhost`: port 8000 for Django/Gunicorn, port 5432 for PostgreSQL, port 6379 for Redis, and port 5000 for OSRM.
   - Enables debug logging and development environment variables.

3. `docker-compose.prod.yml`
   - Configures the hardened production deployment.
   - Adds an `nginx` reverse proxy container on port 80/443 that serves static assets directly and proxies dynamic traffic to Gunicorn.
   - Does not mount local source code. It runs immutable container images built from the multi-stage Dockerfile.
   - Keeps internal service ports (database, Redis, OSRM) private inside the internal Docker network. Only Nginx communicates with the public web.
   - Integrates with external edge routers like Dokploy's Traefik network.

---

## Environment File Separation

Configuration settings are kept separate from code through environment files:

- `.env.example`: Committed template documenting every required variable with safe defaults.
- `.env.dev`: Local development settings. It uses default database passwords, local Redis URLs, and enables Django debug mode.
- `.env.prod`: Production settings. It requires a strong secret key, production database credentials, strict allowed hosts, and secure SSL proxy headers.

The application loads these files automatically depending on the target command. Neither `.env.dev` nor `.env.prod` is committed to git.

---

## Makefile Automation

To avoid typing long Docker Compose commands with multiple `-f` flags, the project includes a root Makefile:

- `make up`: Launches the development stack by merging `docker-compose.base.yml` and `docker-compose.dev.yml` with `.env.dev`.
- `make down`: Stops all running development containers without removing database volumes.
- `make logs`: Streams logs from the backend container.
- `make restart-backend`: Restarts only the web application container after settings changes.
- `make test`: Runs pytest inside the running backend container with full database isolation.
- `make lint`: Executes Ruff and Mypy inside the container to ensure clean code quality.
- `make prod-build`: Builds production container images using Docker buildkit.
- `make prod-up`: Starts the production stack with Nginx.

---

## Network Topology and Service Communication

All containers communicate through an internal Docker bridge network. Service hostnames resolve through Docker internal DNS:

- The `backend` container reaches the database at `db:5432`.
- The `backend` and `worker` reach the cache and Celery broker at `redis:6379`.
- The `backend` reaches the road routing engine at `osrm:5000`.

This naming convention means code never relies on hardcoded IP addresses. Moving containers between physical hosts or cloud servers only requires updating the environment variables.
