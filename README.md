# Fuel Router

Fuel Router is a high-performance Django service and interactive web application for planning long-haul trucking routes across the contiguous United States, determining cost-optimal fuel stops, and minimizing total trip spend under strict vehicle range constraints.

---

## 1. Problem Statement & Constraints

Fuel is the largest controllable operating expense in commercial freight trucking. Given an origin and destination within the contiguous 48 US states, a vehicle with a maximum range of 500 miles, and a constant fuel consumption of 10 miles per gallon (MPG), the application:

- Resolves locations to geographic coordinates.
- Computes the driving route geometry and total distance via OSRM.
- Discovers candidate fuel stations within a 15-mile spatial corridor along the route using PostGIS.
- Applies a greedy-with-lookahead optimization strategy to select fuel stops and compute exact purchase quantities that minimize overall fuel cost.
- Persists every computed trip and its fuel stops to PostgreSQL for immediate re-display without recomputation.
- Decouples plain-language route rationale generation via an asynchronous Celery worker and Fireworks AI LLM adapter.
- Delivers an interactive Leaflet.js map interface alongside a fully featured REST API.

### Invariants & Assumptions
- **Vehicle Range**: 500 miles maximum between refueling stops.
- **Fuel Economy**: Constant 10.0 miles per gallon.
- **Starting State**: The truck departs the origin with a full tank of fuel at zero initial cost (no purchase recorded at mile 0).
- **Geographic Scope**: Contiguous 48 US states only. Requests outside this boundary return a graceful `400 out_of_scope_location` response.
- **Station Pricing**: Sourced from the OPIS truck stop dataset (~8,151 rows). Rows sharing an OPIS Truckstop ID are deduplicated by selecting the minimum retail price.
- **Corridor Buffer**: 15 miles around route geometry to absorb city-centroid geocoding precision.
- **Async AI Isolation**: LLM generation runs in Celery and never delays or blocks core route computation.

---

## 2. Architecture & Design Patterns

The codebase adheres strictly to Clean Architecture and enterprise Python design patterns:

- **Domain Layer (`trips/strategies.py`, `routing/domain.py`)**:
  - `GreedyLookaheadStrategy`: Implements the classic gas-station optimization algorithm. Rather than naively filling to capacity at every stop, the algorithm evaluates reachable stations ahead and only purchases enough fuel to reach cheaper downstream stations, or fills to capacity if current fuel is cheaper than downstream options.
- **Service Layer (`trips/services.py`, `routing/services.py`, `explanations/services.py`)**:
  - `TripPlanningService`: Central orchestrator coordinating geocoding, routing, spatial querying, refueling strategy, persistence, cache-aside, and Celery dispatch.
  - `RoutingService`: Orchestrates route lookups with coordinate validation.
  - `GeocodingService`: Chain of responsibility coordinating local database geocoding and live Nominatim fallback.
  - `ExplanationService`: Formats structured trip payloads and orchestrates LLM prompts.
- **Repository Pattern (`stations/repositories.py`, `trips/repositories.py`)**:
  - Encapsulates spatial PostGIS operations (`find_in_corridor`, `annotate(route_fraction=...)`) and database persistence, preventing ORM leakage into business logic.
- **Adapter Pattern (`routing/adapters/`, `explanations/adapters.py`)**:
  - `OSRMClientAdapter`: Connects to OSRM routing services, returning parsed distance and GeoJSON LineString geometry.
  - `FireworksLLMAdapter`: Integrates with Fireworks AI using the `deepseek-v4p1-flash` model.
  - `LocalGeocoder` and `NominatimGeocoder`: Pluggable geocoding adapters behind a common interface.
- **Cache-Aside Layer (`trips/services.py`)**:
  - Two-tier caching: Redis primary cache with normalized coordinates, PostgreSQL persistence as fallback. Repeated route requests complete in milliseconds with zero external API calls.
- **Asynchronous Worker Layer (`explanations/tasks.py`)**:
  - Celery background task backed by Redis broker. Automatically updates trip records with AI rationales upon completion.

---

## 3. Quick Start

Detailed setup and execution instructions are available in [knowledge/quick-start.md](knowledge/quick-start.md).

### Basic Setup in 4 Steps

```bash
# 1. Configure environment
cp .env.example .env

# 2. Build and start services (web, celery-worker, db, redis)
make build
make up

# 3. Apply database migrations
make migrate

# 4. Ingest and geocode OPIS fuel price data
make load-data
```

Once started, access:
- **Interactive UI**: [http://localhost:8000/](http://localhost:8000/)
- **API Health Check**: [http://localhost:8000/api/health/](http://localhost:8000/api/health/)

### Map Tile Provider (MapTiler Cloud)

Interactive maps on the Trip Detail page use MapTiler Cloud Streets v2 raster tiles with high-DPI 512px resolution.
To configure your free MapTiler API key:
1. Sign up for free at [cloud.maptiler.com](https://cloud.maptiler.com/) (100,000 requests/month free).
2. Add your key to `.env.dev` (or `.env.prod`):
   ```bash
   MAPTILER_API_KEY=your_maptiler_api_key_here
   ```
3. Restart backend:
   ```bash
   make restart-backend
   ```
If `MAPTILER_API_KEY` is omitted, the application gracefully falls back to CARTO Voyager basemaps.

---

## 4. REST API Reference

All REST endpoints are available under the `/api/` path.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health/` | Service health status check |
| `POST` | `/api/trips/` | Plan route, optimize fuel stops, and persist trip |
| `GET` | `/api/trips/` | List recently computed trip plans |
| `GET` | `/api/trips/<uuid:trip_id>/` | Retrieve full trip plan with stops and explanation |

### Example: Plan a Trip

**Request**:
```http
POST /api/trips/
Content-Type: application/json

{
  "start": "Chicago, IL",
  "end": "Dallas, TX"
}
```

**Response (HTTP 200 OK)**:
```json
{
  "id": "6b151003-f1e0-4324-8d89-fd8781ae4766",
  "start_input": "Chicago, IL",
  "end_input": "Dallas, TX",
  "total_distance_miles": 967.4,
  "total_gallons": 96.74,
  "total_cost": 298.45,
  "fuel_stops": [
    {
      "stop_order": 1,
      "station_name": "Pilot Travel Center #123",
      "city": "Mount Vernon",
      "state": "IL",
      "distance_from_start_miles": 278.5,
      "gallons_purchased": 46.74,
      "price_per_gallon": 3.089,
      "cost": 144.38
    }
  ],
  "route_geometry": {
    "type": "LineString",
    "coordinates": [[-87.6298, 41.8781], ...]
  },
  "ai_explanation": "Selected 1 fuel stop along I-57 S. Stop 1 in Mount Vernon, IL was chosen for its low retail price ($3.089/gal) before entering higher-cost regions.",
  "created_at": "2026-09-18T18:45:00Z"
}
```

### Uniform Error Format
All 4xx and 5xx responses use a standardized two-key JSON structure:
```json
{
  "error": "unresolvable_location",
  "detail": "Unable to resolve location: UnknownCityXYZ"
}
```

Standard error codes include `invalid_request`, `unresolvable_location`, `out_of_scope_location`, `routing_unavailable`, `insufficient_station_coverage`, and `not_found`.

---

## 5. Interactive Web Interface

The user interface is built using server-rendered Django templates and Leaflet.js via CDN (zero npm dependencies, zero build steps):

- **Home Page (`/`)**:
  - Origin and destination inputs with validation.
  - 4 quick-select preset benchmark buttons:
    - Chicago, IL to Dallas, TX
    - New York, NY to Los Angeles, CA
    - Seattle, WA to Miami, FL
    - Atlanta, GA to Chicago, IL
  - Past computed trips table with clickable links.
- **Trip Detail Page (`/trips/<uuid:trip_id>/`)**:
  - Interactive Leaflet map with OpenStreetMap tiles and automatic route viewport fitting (`fitBounds`).
  - Color-coded markers: Green (Origin), Red (Destination), Blue numbered badges (Fuel Stops).
  - Stop popups detailing station name, city/state, miles from origin, gallons to fill, unit price, and total stop cost.
  - 4-metric summary bar: Total Distance, Total Fuel Cost, Total Gallons, Stop Count.
  - Sequential turn-by-turn fuel stop breakdown table.
  - AI Route Rationale card with automatic client-side background polling that displays the explanation once Celery finishes without requiring page refresh.

---

## 6. Postman Test Suite

An importable Postman collection is provided at:
```
fuel-router.postman_collection.json
```
It contains pre-built requests for:
- System health check
- All 4 benchmark route presets
- Trip detail retrieval
- Trip history listing
- Error handling scenarios (missing fields, unresolvable locations, non-contiguous states, 404 UUIDs)

---

## 7. Testing & Quality Assurance

```bash
# Run 152 unit and integration tests (100% offline, zero network dependencies)
make test

# Run tests for a specific app or test file
make test TEST_ARGS=trips/tests/

# Run code style formatting (Ruff) and strict type checking (Mypy)
make lint
```

- **Test Suite**: 152 automated tests running in ~2.4 seconds.
- **Static Typing**: Strict Mypy type validation across 88 Python source files with 0 errors.
- **Linting**: Ruff checking with 0 warnings or errors.

---

## 8. Development Commands

| Target | Description |
|---|---|
| `make build` | Build Docker container images |
| `make up` | Start background Docker Compose services |
| `make down` | Stop and remove running containers |
| `make logs` | Stream logs from the Django web service |
| `make restart-backend` | Restart development backend container (alias: `make restart`) |
| `make migrate` | Execute Django database migrations |
| `make load-data` | Run raw import, deduplication, and geocoding pipeline |
| `make test` | Run complete pytest test suite (supports `TEST_ARGS="..."`) |
| `make lint` | Run Ruff linter and Mypy strict type checker |
| `make shell` | Launch interactive Django shell inside web container |
