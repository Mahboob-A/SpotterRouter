# Quick Start Guide

This guide provides step-by-step instructions to set up, populate, test, and run the Fuel Router service locally using Docker Compose and Make.

---

## Prerequisites

Before starting, ensure the following tools are installed on your host system:

- Docker Engine (version 24.0 or newer) and Docker Compose (v2)
- GNU Make
- curl or Postman (for testing HTTP API endpoints)
- A modern web browser (for viewing the Leaflet map UI)

---

## 1. Environment Configuration

The application includes an example environment file `.env.example`. Create your local `.env` file by copying it:

```bash
cp .env.example .env
```

The default values in `.env.example` are pre-configured for local Docker development:

- `SECRET_KEY`: Django cryptographic signing key.
- `DEBUG`: Set to `True` for local development.
- `DATABASE_URL`: `postgis://postgres:postgres@db:5432/fuel_router`
- `REDIS_URL`: `redis://redis:6379/0`
- `CELERY_BROKER_URL`: `redis://redis:6379/1`
- `FIREWORKS_API_KEY`: (Optional) Your Fireworks AI API key.
- `FIREWORKS_LLM_MODEL_NAE`: `accounts/fireworks/models/deepseek-v4p1-flash`

If `FIREWORKS_API_KEY` is not provided, the trip planning engine functions normally; AI explanation generation safely records a non-fatal logged notice without disrupting route calculation.

---

## 2. Start the Docker Stack

Build and start all four services (`db`, `redis`, `web`, and `celery-worker`) in the background:

```bash
make build
make up
```

Verify that all containers are healthy and running:

```bash
docker compose ps
```

Apply database migrations to initialize PostGIS spatial extensions and tables:

```bash
make migrate
```

---

## 3. Ingest and Geocode Station Price Data

The service includes the OPIS fuel price dataset (`fuel-prices-for-be-assessment.csv`) containing over 8,000 retail truck stop entries. Run the unified data pipeline command:

```bash
make load-data
```

This target runs three sequential management commands:

1. `import_stations`: Stages the raw CSV rows into `RawStationPrice`.
2. `load_stations`: Deduplicates stations by OPIS Truckstop ID, picking the lowest retail price per station, and populates the `Station` table.
3. `geocode_stations`: Enriches stations with spatial coordinates using an offline city and state database, falling back to Nominatim for unresolved entries.

---

## 4. Run Automated Tests and Linters

Verify system integrity using the Docker-orchestrated test and lint targets:

```bash
# Run the complete test suite (145 tests, 100% offline)
make test

# Run static analysis (Ruff) and strict type checking (Mypy)
make lint
```

---

## 5. Using the Interactive Web UI

Open your browser and navigate to:

```
http://localhost:8000/
```

### Home View Features
- **Route Input Form**: Enter any origin and destination across the contiguous 48 US states (for example: `Chicago, IL` to `Dallas, TX`).
- **Quick-Select Presets**: Click any preset button to immediately plan and view benchmark routes:
  - Chicago, IL to Dallas, TX
  - New York, NY to Los Angeles, CA
  - Seattle, WA to Miami, FL
  - Atlanta, GA to Chicago, IL
- **Recent Trips History**: Review previously computed routes with direct links to view detailed maps.

### Trip Detail View Features
- **Interactive Leaflet Map**: Rendered using OpenStreetMap tiles with route polyline, green start marker, red finish marker, and numbered fuel stop badges.
- **Stop Popups**: Click any stop marker to inspect station name, address, distance along route, gallons purchased, price per gallon, and stop cost.
- **Metric Summary Cards**: Total distance (miles), total fuel cost (USD), total gallons, and fuel stop count.
- **Fuel Stop Breakdown**: Turn-by-turn table with line item costs.
- **AI Route Rationale**: Displays plain-language explanation generated asynchronously by the Celery worker. If still computing, the interface dynamically polls the backend without requiring a page refresh.

---

## 6. Using the REST API

The service provides clean REST API endpoints for programmatic access.

### Health Check
```bash
curl -s http://localhost:8000/api/health/
```
Response:
```json
{
  "status": "ok"
}
```

### Plan an Optimal Trip
```bash
curl -s -X POST http://localhost:8000/api/trips/ \
  -H "Content-Type: application/json" \
  -d '{"start": "Chicago, IL", "end": "Dallas, TX"}'
```
Response includes:
- `id`: UUID of the persisted trip plan.
- `total_distance_miles`: Total driving distance.
- `total_gallons`: Total fuel required at 10 miles per gallon.
- `total_cost`: Total fuel spend in USD.
- `fuel_stops`: Ordered array of optimal stops with station details, gallons, and costs.
- `route_geometry`: Standard GeoJSON LineString coordinates.
- `ai_explanation`: Asynchronous rationale string (or null if pending).

### Retrieve Trip by ID
```bash
curl -s http://localhost:8000/api/trips/<TRIP_UUID>/
```

### List Recent Trips
```bash
curl -s http://localhost:8000/api/trips/
```

---

## 7. Postman Collection

A pre-configured Postman collection is provided in the repository root:

```
fuel-router.postman_collection.json
```

### Importing into Postman
1. Open Postman.
2. Click **Import** in the upper left navigation.
3. Select `fuel-router.postman_collection.json`.
4. The collection includes pre-built requests for:
   - System health check
   - All 4 benchmark preset route plans
   - Trip detail retrieval
   - Trip history listing
   - Error test cases (empty payload, invalid location, non-contiguous location, non-existent trip ID)

---

## 8. Common Management Commands

All development tasks can be run directly via Make:

| Command | Action |
|---|---|
| `make build` | Build Docker container images |
| `make up` | Start background Docker Compose services |
| `make down` | Stop and tear down running containers |
| `make logs` | Tail web container logs in real time |
| `make migrate` | Apply database migrations |
| `make load-data` | Execute full station data ingestion sequence |
| `make test` | Execute test suite using pytest |
| `make lint` | Run Ruff linter and Mypy strict type checker |
| `make shell` | Open interactive Django shell inside web container |
