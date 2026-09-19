# Clean Architecture and Domain Isolation

## The Core Philosophy
When building SpotterRouter, one of the first major technical decisions was to separate the core business rules from Django itself. In many Django projects, business logic gets tangled inside models (`models.py`) or views (`views.py`). That works for small CRUD apps, but for route optimization, fuel math, and spatial queries, it quickly turns into a mess that is hard to test and maintain.

I wanted the core optimization engine to be completely pure Python. It should not care whether the data came from PostgreSQL, a CSV file, an in-memory dictionary during unit testing, or a mock network call.

```text
+-------------------------------------------------------------------+
|                        PRESENTATION LAYER                         |
|         Django Templates (HTML/JS/CSS)   |   REST API (DRF)       |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                        APPLICATION LAYER                          |
|    TripPlanningService   |   DatasetIngestionService              |
|    TripPdfReportService  |   ExplanationCoordinatorService        |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                           DOMAIN LAYER                            |
|    Pure Python Dataclasses (RouteCorridor, RefuelStop, FuelCost)  |
|    Greedy Lookahead Optimization Algorithm (Zero Django Imports)  |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                       INFRASTRUCTURE LAYER                        |
|    PostGIS Spatial Repositories   |   Redis Cache Client          |
|    OSRM Open-Source Router Adapter|   Fireworks DeepSeek Client   |
+-------------------------------------------------------------------+
```

## The Four Concentric Layers

### 1. The Domain Layer (`trips/domain/` and `routing/domain/`)
The domain layer contains our fundamental data objects and mathematical calculations:
- Plain Python dataclasses such as `RouteCoordinate`, `RouteCorridor`, `CandidateStation`, and `OptimizedRefuelPlan`.
- The greedy lookahead refueling algorithm.
- Zero dependencies on Django ORM, Celery, or external HTTP clients.
- Can be tested in sub-millisecond unit tests without needing a database connection.

### 2. The Application Services Layer (`trips/services.py`, `stations/services.py`)
Application services coordinate work across the domain and infrastructure:
- `TripPlanningService`: Resolves coordinates, checks Redis cache, calls routing adapters, invokes PostGIS station searches, and executes the optimization engine.
- `DatasetIngestionService`: Reads CSV rows, validates schemas, runs zip code geocoding, computes SHA-256 hashes, and handles atomic database activation.
- `TripPdfReportService`: Formats calculated plans into clean multi-page dispatch documents using ReportLab.

### 3. The Repository and Adapter Layer (`trips/repositories.py`, `stations/repositories.py`)
All database access is encapsulated behind clean repository interfaces:
- The domain and service layers never run raw SQL or direct ORM `.filter()` calls.
- `StationRepository` handles PostGIS spatial queries like `ST_DWithin` and `ST_LineLocatePoint`.
- `TripPlanRepository` saves computed trips and their spatial geometry into the database.
- If we ever want to switch from PostgreSQL to another spatial database or mock the database during unit tests, we only need to write a new repository class.

### 4. The Presentation Layer (`ui/` and `api/`)
The presentation layer handles HTTP requests and returns user-friendly responses:
- Django views render clean server-side HTML pages.
- Django REST Framework views provide JSON endpoints for third-party consumers.
- Input validation handles user errors before they ever reach the domain logic.

## Why This Matters for the Assessment
1. **Testability**: Over 80% of our test suite runs purely in-memory in fractions of a second because business logic has no database dependencies.
2. **Resilience**: If an external provider like OSRM or the AI service goes down, the boundaries make it straightforward to plug in mock fallbacks without breaking the application.
3. **Clarity**: Any engineer reviewing this codebase can open `trips/services.py` and immediately understand the step-by-step route planning lifecycle without getting distracted by SQL queries or HTML formatting.
