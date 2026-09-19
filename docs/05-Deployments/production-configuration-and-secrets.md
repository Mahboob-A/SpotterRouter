# Production Configuration and Secret Management

## Overview

Deploying an application to production requires careful handling of secrets, environment variables, database volumes, and security headers. This guide outlines how SpotterRouter configures production security and data persistence.

---

## Required Production Environment Variables

The following environment variables must be configured in the Dokploy web dashboard (under the Environment tab) before launching the stack:

| Variable | Description | Example / Recommendation |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret cryptographic key used by Django sessions and CSRF signing | Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | Disables debug mode in production to avoid leaking traceback details | Must be set to `False` |
| `ALLOWED_HOSTS` | Comma-separated list of valid domain names | `spotterrouter.com,www.spotterrouter.com,localhost` |
| `CSRF_TRUSTED_ORIGINS` | Permitted origins for POST submissions over HTTPS | `https://spotterrouter.com,https://www.spotterrouter.com` |
| `POSTGRES_DB` | Production PostgreSQL database name | `fuel_router` |
| `POSTGRES_USER` | PostgreSQL superuser username | `spotter` |
| `POSTGRES_PASSWORD` | Strong password for PostgreSQL authentication | Random 32-character string |
| `MAPTILER_API_KEY` | MapTiler Cloud token for map tiles | Production key with HTTP referer restrictions |
| `DEEPSEEK_API_KEY` | AI explanation API token (optional) | DeepSeek platform API key |

---

## Reverse Proxy Header Configuration

Because Dokploy routes HTTPS traffic through Traefik before it reaches Django, Django receives incoming requests over HTTP on internal port 8000. Without proper proxy header configuration, Django might believe requests are insecure and reject CSRF tokens or redirect in an infinite HTTPS loop.

To prevent this, `fuel_router/settings.py` includes:

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
```

This tells Django to trust the `X-Forwarded-Proto` and `X-Forwarded-Host` headers supplied by Traefik.

---

## Persistent Named Volumes

Containers are ephemeral by default, meaning any data written inside a container filesystem is lost when that container is destroyed or updated. SpotterRouter configures persistent Docker named volumes for all stateful data:

1. `postgres_data`: Mounted at `/var/lib/postgresql/data` in the database container. Ensures station coordinates, prices, and computed trip records survive container restarts and image updates.
2. `dataset_data`: Mounted at `/app/dataset` in the backend container. Preserves uploaded CSV files across releases.
3. `osrm_data`: Stores the pre-processed road network graph files so OSRM does not need to re-extract geometry on startup.

---

## Static Volume Permissions

During production deployments, static assets are collected during image build into `/app/staticfiles/`. When deploying on Linux hosts with non-root Docker configurations:
- Ensure the static assets directory is owned by the container application user (`appuser`).
- If mounting a host directory, verify permissions with `chmod -R 755 staticfiles`.
