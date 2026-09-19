# How I Prepared and Planned the Assessment

## The Preparation Mindset
When starting an engineering assessment with multiple complex moving parts (spatial queries, routing algorithms, PDF generation, AI integration, responsive UI, and containerization), the temptation is often to jump straight into code.
Doing that usually leads to architectural debt, rewritten code, and messy git histories.

I approached this assessment with an engineering discipline focused on:
1. Deconstructing requirements into atomic, testable milestones.
2. Establishing infrastructure and container reproducibility on Day 1.
3. Writing domain logic first before database models.
4. Making atomic git commits with clear conventional commit messages.

```text
                        THE STEP-BY-STEP ROADMAP
[1. Infrastructure Setup] ---> Docker Compose, PostGIS, Redis, Celery, Makefile
           |
           v
[2. Data Layer & Ingestion] -> Offline Zip Geocoder, SHA-256 Checksums, Versioning
           |
           v
[3. Core Optimization Engine]-> Pure Python Domain, Lookahead Horizon Algorithm
           |
           v
[4. Application Services] ---> OSRM Router, PostGIS Corridor Buffer, Two-Tier Cache
           |
           v
[5. Async AI Pipeline] ------> Celery Worker, Fireworks DeepSeek, Real-time Polling
           |
           v
[6. Polished UI & PDF] ------> Interactive Map, Dispatch Sheet PDF, VS Code Docs
```

---

## The Execution Strategy

### Step 1: Container Parity from the First Minute
Before writing any business logic, I established the multi-stage `Dockerfile` and `docker-compose.yml` hierarchy.
Ensuring that C spatial libraries (`libgdal-dev`, `libgeos-dev`, `libproj-dev`), PostgreSQL with PostGIS extensions, Redis, and Celery ran identically in both development and production eliminated all "works on my machine" issues.

### Step 2: Isolating the Core Domain
Instead of starting with Django models, I designed the fuel optimization problem in pure Python.
I created test suites with mock stations and mock routes to verify that the lookahead algorithm correctly handled runway calculations, edge cases, and price horizons. Only after the mathematical engine was proven did I connect it to PostGIS.

### Step 3: Incremental Milestone Commits
Every feature was developed on an isolated branch off an updated `main` branch, tested with unit and integration tests, verified with `make lint` and `make test`, and merged with clean conventional commit formatting:
`feat(scope): descriptive summary`
`fix(scope): descriptive summary`

### Step 4: Constant Alignment and Verification
After each major milestone (such as dataset versioning, fuel calculation alignment, PDF export, and MapTiler tile migration), I verified real routes through both the API and browser UI to ensure calculations matched down to the gallon and cent.
