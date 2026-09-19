# Zero Downtime Release and Health Checks

## Overview

When updating code, applying database migrations, or deploying new features in production, users should not experience dropped connections or downtime. This guide explains how SpotterRouter performs zero-downtime deployments and validates system health.

---

## The Release Workflow

A typical production release on Dokploy follows this pipeline:

1. Push to Repository
   The developer merges verified changes to the target branch. Dokploy detects the new commit or receives a webhook.

2. Image Build
   Docker builds the updated application image using Docker buildkit. Static assets are collected and Python packages are installed into a clean virtual environment.

3. Database Migrations
   Before switching live traffic to the new image, database migrations are applied:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate
   ```
   Or via the Makefile:
   ```bash
   make prod-migrate
   ```

4. Container Swap
   Docker starts the new application container alongside the old one. Once the new container passes health probes, Traefik switches routing to the new container and shuts down the old one.

---

## Health Check Probe Validation

The application exposes a dedicated health check endpoint at `/api/health/`.

When called with a `GET` request, the health view verifies:
1. Database connectivity: Executes a lightweight database ping to ensure PostgreSQL and PostGIS extensions are active.
2. Redis connectivity: Pings the Redis instance to confirm the cache and message broker are ready.
3. System status: Returns an HTTP 200 OK with `{"status": "ok"}` when all checks succeed.

If any core dependency fails, the endpoint returns an HTTP 503 error, alerting Docker and Traefik not to route traffic to an unhealthy container.

---

## Monitoring and Logs

During and after deployment, engineers can monitor live container output:

- View all service logs:
  ```bash
  docker compose -f docker-compose.prod.yml logs -f --tail=100
  ```
- View only the backend web server:
  ```bash
  docker compose -f docker-compose.prod.yml logs -f backend
  ```
- View Celery task worker output:
  ```bash
  docker compose -f docker-compose.prod.yml logs -f worker
  ```

---

## Post-Deployment Verification Checklist

After a release completes, run through this short smoke test checklist:

1. Visit the homepage: Verify the UI loads cleanly with Leaflet map tiles.
2. Check health: Run `curl -I https://your-domain.com/api/health/` and confirm HTTP 200.
3. Plan a route: Run a test calculation between Chicago, IL and Dallas, TX to ensure OSRM and the greedy refuel solver produce expected outputs.
4. Verify cache header: Inspect response headers and confirm `X-Cache` is returned.
5. Check Swagger UI: Open `/api-docs/` to confirm interactive API documentation is accessible.

---

## Rollback Strategy

If a critical issue is discovered post-release:
1. In the Dokploy web dashboard, select the previous successful deployment and click "Redeploy".
2. Alternatively, revert the git commit on the release branch and push to trigger an automated rollback.
3. If migrations were applied, run `python manage.py migrate <app_name> <migration_name>` inside the container to roll back schema changes safely.
