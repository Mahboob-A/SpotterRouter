# SpotterRouter

Intelligent Long-Haul Fuel Route Optimization Engine for Contiguous US Commercial Fleets.

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Django 6.1](https://img.shields.io/badge/Django-6.1-092E20.svg?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL 17 / PostGIS 3.5](https://img.shields.io/badge/PostGIS-17--3.5-336791.svg?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Redis 8](https://img.shields.io/badge/Redis-8.0-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Celery 5.5](https://img.shields.io/badge/Celery-5.5-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Tests Passed](https://img.shields.io/badge/Tests-228%20Passed-22c55e.svg?logo=pytest&logoColor=white)](/)
[![Mypy Strict](https://img.shields.io/badge/Types-Mypy%20Strict-2563eb.svg)](/)
[![Ruff Lint](https://img.shields.io/badge/Linter-Ruff-261230.svg?logo=ruff&logoColor=white)](/)
[![OpenAPI 3.0](https://img.shields.io/badge/OpenAPI-3.0.3-6BA539.svg?logo=openapi-initiative&logoColor=white)](/openapi.yaml)
[![Dokploy Ready](https://img.shields.io/badge/Deploy-Dokploy-000000.svg)](/docs/?doc=05-Deployments/dokploy-platform-deployment-and-traefik)

---

## Application Routes & Live Navigation

The application provides server-rendered interfaces alongside REST APIs. All links below use relative paths so they work in both local development and production environments:

| Route | Name | Purpose & Why It Exists |
|---|---|---|
| `[/](/)` | **Trip Planner & Dashboard** | Main interface to plan routes, preview benchmark pairs, view fuel stops on an interactive Leaflet map, and inspect recent trip history. |
| `[/locations/](/locations/)` | **Location Explorer** | Search and browse supported contiguous US cities, states, and coordinates to verify geocoding coverage before dispatching. |
| `[/datasets/](/datasets/)` | **Dataset Manager** | Inspect active OPIS fuel price data, upload new CSVs, verify SHA-256 hashes, and switch active datasets in real time without downtime. |
| `[/docs/](/docs/)` | **Engineering Documentation** | Built-in VS Code-style interactive reader containing 24 comprehensive articles covering architecture, algorithms, tradeoffs, infra, and deployments. |
| `[/api-docs/](/api-docs/)` | **Interactive Swagger UI** | Test and explore the REST API directly in the browser with live parameter execution and schema validation. |
| `[/openapi.yaml](/openapi.yaml)` | **OpenAPI Specification** | Raw OpenAPI 3.0 YAML specification file ready for import into Postman, Insomnia, or client SDK generators. |
| `[/api/health/](/api/health/)` | **System Health Check** | Machine-readable health check verifying connectivity to PostgreSQL/PostGIS, Redis, and OSRM routing services. |
| `[/trips/<id>/pdf/](/trips/<id>/pdf/)` | **Driver Dispatch PDF** | In-memory commercial driver dispatch sheet with turn-by-turn refueling instructions and safety checklists. |

---

## Deep-Dive Documentation

For thorough explanations of design choices, math, tradeoffs, infrastructure, and lessons learned, explore the dedicated documentation suite at `[/docs/](/docs/)`:

- **01 System architecture**: Clean architecture layer boundaries, domain isolation, two-tier cache-aside with Redis and PostGIS, and the asynchronous Celery pipeline.
- **02 Current implemented system**: PostGIS spatial corridor matching (`ST_LineLocatePoint`), greedy lookahead refueling algorithm, in-memory PDF engine, and dataset versioning.
- **03 Design decisions and tradeoffs**: Local filesystem vs cloud storage, OpenStreetMap direct tiles vs MapTiler Cloud, and synchronous vs asynchronous AI rationales.
- **04 Infrastructure architecture**: Multi-environment Docker Compose files, Nginx reverse proxy edge routing, Redis hit/miss lifecycle with `X-Cache` headers, and operational choices.
- **05 Production deployments**: Dokploy platform deployment, Traefik edge ingress, automated SSL, secret management, and zero-downtime rolling releases.
- **06 Brainstorming and failed paths**: First attempts that did not work (midpoint stops, unindexed bounding boxes, full-tank fills) and why the final approach succeeded.
- **07 What I learned**: Personal engineering reflections on PostGIS spatial queries, greedy algorithms, and US freight logistics.
- **08 Preparation and engineering standards**: Implementation roadmap, 228 automated tests, strict static typing, and Docker container parity.

---

## Problem Statement & Rules

Fuel represents the single highest variable cost in long-haul trucking. SpotterRouter calculates the cost-minimal refueling schedule for commercial trucks traveling across the contiguous 48 US states:

1. **Vehicle Constraints**: 500-mile maximum tank runway, constant 10.0 MPG fuel consumption.
2. **Initial Condition**: Vehicle departs the origin with a full tank of fuel at zero initial cost.
3. **Corridor Discovery**: PostGIS discovers candidate stations within a 15-mile buffer along the OSRM route.
4. **Greedy Optimization**: Purchases only enough fuel to reach cheaper stations downstream, or tops up when current fuel is cheaper than downstream options.
5. **Two-Tier Caching**: Checks Redis normalized coordinate cache first, falls back to PostGIS persistent records, and sets `X-Cache: HIT` or `X-Cache: MISS` headers.
6. **Async AI Rationale**: An asynchronous Celery worker generates plain-language route reasoning via Fireworks AI without delaying route computation.

---

## Quick Start

Detailed instructions are available in [knowledge/quick-start.md](knowledge/quick-start.md).

```bash
# 1. Initialize environment files
make setup-env

# 2. Build and start development stack (web, celery-worker, db, redis)
make build
make up

# 3. Apply database migrations
make migrate

# 4. Ingest and geocode OPIS fuel price dataset
make load-data
```

Once running:
- Web Application: [http://localhost:8000/](http://localhost:8000/)
- Swagger API Docs: [http://localhost:8000/api-docs/](http://localhost:8000/api-docs/)
- System Health Check: [http://localhost:8000/api/health/](http://localhost:8000/api/health/)

### Map Tile Configuration (MapTiler Cloud)
To render high-DPI vector tiles on map views:
1. Obtain a free key from [cloud.maptiler.com](https://cloud.maptiler.com/).
2. Add `MAPTILER_API_KEY=your_key_here` to `.env.dev` (or `.env.prod`).
3. Run `make restart-backend`. If omitted, CARTO Voyager basemaps are used automatically.

---

## REST API Summary

All endpoints return structured JSON with uniform error envelopes (`{"error": "...", "detail": "..."}`).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health/` | Service health status check |
| `POST` | `/api/trips/` | Plan route, optimize fuel stops, and persist trip (`force_refresh` supported) |
| `GET` | `/api/trips/` | List recently computed trip plans |
| `GET` | `/api/trips/<uuid:trip_id>/` | Retrieve full trip plan with stops and AI rationale |

Example trip request:
```http
POST /api/trips/
Content-Type: application/json

{
  "start": "Chicago, IL",
  "end": "Dallas, TX",
  "force_refresh": false
}
```

---

## Quality Assurance & Testing

```bash
# Run the complete test suite (228 tests, 100% offline, zero external API calls)
make test

# Run Ruff linter and strict Mypy type validation
make lint
```

- **Test Coverage**: 228 automated pytest unit and integration tests passing in under 5 seconds.
- **Type Safety**: Strict Mypy compliance across all 102 Python source files with zero errors.
- **Code Standards**: Ruff linting clean across the entire repository.

---

## Development Commands

| Command | Description |
|---|---|
| `make setup-env` | Initialize `.env.dev` and `.env.prod` from `.env.example` |
| `make up` | Start development stack with automatic environment setup |
| `make down` | Stop development stack |
| `make build` | Build development Docker images |
| `make logs` | Stream live backend container logs |
| `make restart-backend` | Restart backend service (alias: `make restart`) |
| `make migrate` | Execute Django database migrations |
| `make load-data` | Ingest, deduplicate, and geocode active station dataset |
| `make test` | Run pytest suite inside backend container |
| `make lint` | Run Ruff and Mypy checks inside backend container |
| `make shell` | Open interactive Django shell inside backend container |
| `make prod-build` | Build multi-stage production Docker images |
| `make prod-up` | Start production stack with Nginx edge proxy |
| `make prod-down` | Stop production stack |
| `make prod-logs` | Stream production stack logs |
