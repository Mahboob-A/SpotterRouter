from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings

from ui.docs_parser import ParsedDocument, TocItem, parse_markdown


@dataclass(frozen=True)
class DocMetadata:
    slug: str
    category_id: str
    category_title: str
    title: str
    filename: str
    summary: str
    reading_time_minutes: int


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    docs: list[DocMetadata]


@dataclass(frozen=True)
class DocDetail:
    metadata: DocMetadata
    html_content: str
    table_of_contents: list[TocItem]
    previous_doc: DocMetadata | None
    next_doc: DocMetadata | None


DOCS_CATALOG_DATA: list[dict[str, Any]] = [
    {
        "id": "01-Architecture",
        "title": "01 System Architecture",
        "docs": [
            {
                "slug": (
                    "01-Architecture/clean-architecture-and-domain-isolation"
                ),
                "title": "Clean Architecture and Domain Isolation",
                "filename": "clean-architecture-and-domain-isolation.md",
                "summary": (
                    "Decoupling core business rules from Django models "
                    "and external routing APIs using clean layer boundaries."
                ),
            },
            {
                "slug": "01-Architecture/two-tier-caching-and-cache-aside",
                "title": "Two-Tier Caching and Cache-Aside Pattern",
                "filename": "two-tier-caching-and-cache-aside.md",
                "summary": (
                    "Using Redis for normalized coordinate routes and PostGIS "
                    "for immutable trip plan persistence."
                ),
            },
            {
                "slug": (
                    "01-Architecture/asynchronous-celery-worker-pipeline"
                ),
                "title": "Asynchronous Celery Worker Pipeline",
                "filename": "asynchronous-celery-worker-pipeline.md",
                "summary": (
                    "Offloading LLM explanation generation to Celery workers "
                    "so route calculations respond in under 100 milliseconds."
                ),
            },
        ],
    },
    {
        "id": "02-Current-system",
        "title": "02 Current Implemented System",
        "docs": [
            {
                "slug": "02-Current-system/postgis-spatial-corridor-matching",
                "title": "PostGIS Spatial Corridor Station Matching",
                "filename": "postgis-spatial-corridor-matching.md",
                "summary": (
                    "Querying fuel stations within 15 miles of the route corridor "
                    "and projecting station distances using ST_LineLocatePoint."
                ),
            },
            {
                "slug": "02-Current-system/greedy-lookahead-refueling-engine",
                "title": "Greedy Lookahead Refueling Engine",
                "filename": "greedy-lookahead-refueling-engine.md",
                "summary": (
                    "Managing 500-mile truck runway, 10 MPG consumption, and "
                    "dynamic gallon purchasing to minimize overall trip fuel cost."
                ),
            },
            {
                "slug": "02-Current-system/in-memory-dispatch-pdf-generator",
                "title": "In-Memory Dispatch PDF Generator",
                "filename": "in-memory-dispatch-pdf-generator.md",
                "summary": (
                    "Building multi-page commercial driver dispatch sheets "
                    "with ReportLab streaming directly into HTTP responses."
                ),
            },
            {
                "slug": (
                    "02-Current-system/dataset-versioning-and-csv-ingestion"
                ),
                "title": "Dataset Versioning and CSV Ingestion",
                "filename": "dataset-versioning-and-csv-ingestion.md",
                "summary": (
                    "Uploading, validating, SHA-256 hashing, and activating "
                    "OPIS fuel price datasets with zero application downtime."
                ),
            },
        ],
    },
    {
        "id": "03-Tradeoffs",
        "title": "03 Design Decisions and Tradeoffs",
        "docs": [
            {
                "slug": "03-Tradeoffs/local-filesystem-vs-cloud-s3",
                "title": "Local Filesystem vs Cloud S3 Storage",
                "filename": "local-filesystem-vs-cloud-s3.md",
                "summary": (
                    "Why local disk and in-memory streams are used for the assessment "
                    "demo, and how the cloud architecture scales to S3."
                ),
            },
            {
                "slug": "03-Tradeoffs/osm-direct-tiles-vs-maptiler-cloud",
                "title": "OSM Direct Tiles vs MapTiler Cloud",
                "filename": "osm-direct-tiles-vs-maptiler-cloud.md",
                "summary": (
                    "Diagnosing the OpenStreetMap volunteer server 403 policy block "
                    "and migrating to MapTiler Cloud Streets v2 tiles."
                ),
            },
            {
                "slug": (
                    "03-Tradeoffs/synchronous-vs-async-ai-explanations"
                ),
                "title": "Synchronous vs Asynchronous AI Explanations",
                "filename": "synchronous-vs-async-ai-explanations.md",
                "summary": (
                    "Analyzing UX responsiveness: why blocking HTTP requests for "
                    "large language models is avoided in production."
                ),
            },
        ],
    },
    {
        "id": "04-Infra",
        "title": "04 Infrastructure Architecture",
        "docs": [
            {
                "slug": (
                    "04-Infra/docker-compose-and-environment-architecture"
                ),
                "title": "Docker Compose and Multi-Environment Architecture",
                "filename": "docker-compose-and-environment-architecture.md",
                "summary": (
                    "Architecture of development, production, and base Docker "
                    "Compose topologies with isolated networking."
                ),
            },
            {
                "slug": "04-Infra/nginx-reverse-proxy-and-edge-routing",
                "title": "Nginx Reverse Proxy and Edge Routing",
                "filename": "nginx-reverse-proxy-and-edge-routing.md",
                "summary": (
                    "Placement of Nginx as an edge gateway, static asset streaming, "
                    "buffer tuning, and upstream proxying."
                ),
            },
            {
                "slug": "04-Infra/redis-caching-and-hit-miss-lifecycle",
                "title": "Redis Caching and Hit-Miss Lifecycle",
                "filename": "redis-caching-and-hit-miss-lifecycle.md",
                "summary": (
                    "Cache resolution lifecycle, TTL strategies, dataset version "
                    "invalidation, and the X-Cache HTTP header."
                ),
            },
            {
                "slug": (
                    "04-Infra/infrastructure-tradeoffs-and-operational-choices"
                ),
                "title": "Infrastructure Tradeoffs and Operational Choices",
                "filename": "infrastructure-tradeoffs-and-operational-choices.md",
                "summary": (
                    "Evaluating container setups, reverse proxy placement, caching "
                    "layers, and database scaling boundaries."
                ),
            },
        ],
    },
    {
        "id": "05-Deployments",
        "title": "05 Production Deployments",
        "docs": [
            {
                "slug": (
                    "05-Deployments/dokploy-platform-deployment-and-traefik"
                ),
                "title": "Dokploy Platform Deployment and Traefik Ingress",
                "filename": "dokploy-platform-deployment-and-traefik.md",
                "summary": (
                    "Deploying Fuel Router on Dokploy, configuring Traefik edge "
                    "routing, SSL automation, and container orchestration."
                ),
            },
            {
                "slug": (
                    "05-Deployments/production-configuration-and-secrets"
                ),
                "title": "Production Configuration and Secrets Management",
                "filename": "production-configuration-and-secrets.md",
                "summary": (
                    "Managing production environment variables, database credentials, "
                    "API keys, and secret rotation patterns."
                ),
            },
            {
                "slug": (
                    "05-Deployments/zero-downtime-release-and-health-checks"
                ),
                "title": "Zero-Downtime Release and Health Checks",
                "filename": "zero-downtime-release-and-health-checks.md",
                "summary": (
                    "Automating safe database migrations, container readiness probes, "
                    "and graceful zero-downtime deployments."
                ),
            },
        ],
    },
    {
        "id": "06-Brainstorming-and-failed-paths",
        "title": "06 Brainstorming and Failed Paths",
        "docs": [
            {
                "slug": (
                    "06-Brainstorming-and-failed-paths/what-did-not-work-first-attempts"
                ),
                "title": "What Did Not Work - First Attempts and Failed Paths",
                "filename": "what-did-not-work-first-attempts.md",
                "summary": (
                    "Four failed ideas: midpoint stops, unindexed bounding "
                    "box queries, full-tank fills everywhere, and OSM tiles."
                ),
            },
            {
                "slug": (
                    "06-Brainstorming-and-failed-paths/what-worked-well-and-why"
                ),
                "title": "What Worked Well and Why",
                "filename": "what-worked-well-and-why.md",
                "summary": (
                    "Winning architectural choices: greedy lookahead horizons, "
                    "spatial corridor buffers, and dataset-keyed caching."
                ),
            },
        ],
    },
    {
        "id": "07-Learning-journey",
        "title": "07 What I Learned",
        "docs": [
            {
                "slug": (
                    "07-Learning-journey/first-time-with-postgis-and-spatial-sql"
                ),
                "title": "First Time with PostGIS and Spatial SQL",
                "filename": "first-time-with-postgis-and-spatial-sql.md",
                "summary": (
                    "Personal learning story: understanding geography types, "
                    "SRID 4326, GiST spatial indexing, and ST_LineLocatePoint."
                ),
            },
            {
                "slug": (
                    "07-Learning-journey/"
                    "first-time-with-greedy-lookahead-algorithms"
                ),
                "title": "First Time with Greedy Lookahead Algorithms",
                "filename": "first-time-with-greedy-lookahead-algorithms.md",
                "summary": (
                    "Discovering the vehicle refueling problem, studying lookahead "
                    "heuristics, and designing practical fuel runway safety math."
                ),
            },
            {
                "slug": (
                    "07-Learning-journey/"
                    "learning-the-usa-freight-and-fuel-ecosystem"
                ),
                "title": "Learning the USA Freight and Fuel Ecosystem",
                "filename": "learning-the-usa-freight-and-fuel-ecosystem.md",
                "summary": (
                    "Understanding Class 8 truck fuel tanks, 500-mile operational "
                    "ranges, 10 MPG consumption, and OPIS rack diesel pricing."
                ),
            },
        ],
    },
    {
        "id": "08-Preparation-and-testing",
        "title": "08 Preparation and Engineering Standards",
        "docs": [
            {
                "slug": "08-Preparation-and-testing/how-i-prepared-and-planned",
                "title": "How I Prepared and Planned the Assessment",
                "filename": "how-i-prepared-and-planned.md",
                "summary": (
                    "Deconstructing assessment requirements, planning incremental "
                    "milestones, and maintaining strict git commit hygiene."
                ),
            },
            {
                "slug": (
                    "08-Preparation-and-testing/testing-strategy-and-quality-checks"
                ),
                "title": "Testing Strategy and Quality Checks",
                "filename": "testing-strategy-and-quality-checks.md",
                "summary": (
                    "Overview of 186 unit and integration tests, strict Mypy types, "
                    "Ruff linting, and Docker container parity."
                ),
            },
        ],
    },
]


class DocsService:
    """Service to load, index, and cache assessment documentation."""

    def __init__(self, docs_root: Path | None = None) -> None:
        self._docs_root = docs_root or (Path(settings.BASE_DIR) / "docs")
        self._categories: list[Category] = []
        self._flat_docs: list[DocMetadata] = []
        self._slug_to_meta: dict[str, DocMetadata] = {}
        self._cache_parsed: dict[str, ParsedDocument] = {}
        self._build_catalog()

    def _build_catalog(self) -> None:
        categories: list[Category] = []
        flat_docs: list[DocMetadata] = []
        slug_to_meta: dict[str, DocMetadata] = {}

        for cat_data in DOCS_CATALOG_DATA:
            cat_docs: list[DocMetadata] = []
            for doc_info in cat_data["docs"]:
                meta = DocMetadata(
                    slug=doc_info["slug"],
                    category_id=cat_data["id"],
                    category_title=cat_data["title"],
                    title=doc_info["title"],
                    filename=doc_info["filename"],
                    summary=doc_info["summary"],
                    reading_time_minutes=self._estimate_reading_time(
                        cat_data["id"], doc_info["filename"]
                    ),
                )
                cat_docs.append(meta)
                flat_docs.append(meta)
                slug_to_meta[meta.slug] = meta

            categories.append(
                Category(
                    id=cat_data["id"],
                    title=cat_data["title"],
                    docs=cat_docs,
                )
            )

        self._categories = categories
        self._flat_docs = flat_docs
        self._slug_to_meta = slug_to_meta

    def _estimate_reading_time(self, category_id: str, filename: str) -> int:
        file_path = self._docs_root / category_id / filename
        if not file_path.is_file():
            return 3
        try:
            content = file_path.read_text(encoding="utf-8")
            words = len(content.split())
            return max(1, round(words / 200))
        except Exception:
            return 3

    def get_categories(self) -> list[Category]:
        return self._categories

    def get_flat_docs(self) -> list[DocMetadata]:
        return self._flat_docs

    def get_default_slug(self) -> str:
        if self._flat_docs:
            return self._flat_docs[0].slug
        return "01-Architecture/clean-architecture-and-domain-isolation"

    def get_doc_detail(self, slug: str) -> DocDetail | None:
        clean_slug = slug.strip().strip("/")
        meta = self._slug_to_meta.get(clean_slug)
        if not meta:
            return None

        file_path = self._docs_root / meta.category_id / meta.filename
        raw_markdown = ""
        if file_path.is_file():
            raw_markdown = file_path.read_text(encoding="utf-8")
        else:
            raw_markdown = (
                f"# {meta.title}\n\n"
                f"> Note: Content for {meta.filename} is being compiled.\n\n"
                f"{meta.summary}\n"
            )

        if clean_slug not in self._cache_parsed:
            self._cache_parsed[clean_slug] = parse_markdown(raw_markdown)

        parsed = self._cache_parsed[clean_slug]

        # Determine previous and next docs for linear navigation
        prev_doc: DocMetadata | None = None
        next_doc: DocMetadata | None = None
        for i, item in enumerate(self._flat_docs):
            if item.slug == clean_slug:
                if i > 0:
                    prev_doc = self._flat_docs[i - 1]
                if i < len(self._flat_docs) - 1:
                    next_doc = self._flat_docs[i + 1]
                break

        return DocDetail(
            metadata=meta,
            html_content=parsed.html_content,
            table_of_contents=parsed.table_of_contents,
            previous_doc=prev_doc,
            next_doc=next_doc,
        )

    def search_docs(self, query: str) -> list[DocMetadata]:
        term = query.strip().lower()
        if not term:
            return self._flat_docs
        return [
            doc
            for doc in self._flat_docs
            if term in doc.title.lower()
            or term in doc.summary.lower()
            or term in doc.slug.lower()
        ]
