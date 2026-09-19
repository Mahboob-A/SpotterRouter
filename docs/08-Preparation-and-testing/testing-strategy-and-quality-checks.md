# Testing Strategy and Quality Checks

## The Philosophy of Rigorous Testing
A software system that handles logistics and financial calculations must be backed by a thorough, deterministic test suite. If a fuel routing calculation breaks or miscalculates fuel gallons, a commercial truck could literally run out of diesel on the highway.

Our testing strategy follows the testing pyramid:
- Extensive, lightning-fast unit tests at the base (pure Python domain logic).
- Service and repository integration tests in the middle (PostGIS queries, caching, dataset ingestion).
- End-to-end view and API endpoint tests at the top (HTTP status codes, PDF streaming, templates).

```text
               THE TESTING & QUALITY PYRAMID
                     / \
                    /   \     End-to-End View & API Tests (32 tests)
                   /-----\    - HTTP responses, PDF generation, docs viewer
                  /       \   Integration & Repository Tests (64 tests)
                 /---------\  - PostGIS spatial buffers, Redis cache, ingestion
                /           \ Unit & Mathematical Tests (90+ tests)
               /-------------\- Pure lookahead algorithm, runway math, parser
```

---

## The Quality Standards Enforced

### 1. Strict Type Safety with Mypy
The entire codebase runs under Python 3.13 with strict type checking enabled:
```ini
[tool.mypy]
python_version = "3.13"
strict = true
warn_unused_ignores = true
warn_return_any = true
disallow_untyped_defs = true
```
Every function, class, and method has explicit parameter and return type hints. Running `make lint` checks 98+ source files and enforces complete type integrity across domain, service, and view layers.

### 2. Modern Linting and Formatting with Ruff
We use Ruff for lightning-fast linting and code hygiene:
- Line length enforced at 88 characters.
- Unused imports, variable shadowing, and syntax bugs caught instantly.
- Consistent PEP 8 formatting enforced across all apps.

### 3. Isolation and Deterministic Test Fixtures
- Tests never make live external HTTP calls to OSRM, OpenStreetMap, or Fireworks AI.
- External adapters are mocked using deterministic fixtures with real geographic coordinates.
- Route calculations produce identical, reproducible results across any machine or CI/CD runner.

### 4. Running the Quality Suite
Developers and reviewers can run the entire test and quality verification suite inside Docker with two simple commands:
```bash
# Run linters and type checkers across all files
make lint

# Run the full automated test suite with pytest
make test
```
All tests execute in a clean, reproducible container environment, ensuring 100% confidence before any code is merged.
