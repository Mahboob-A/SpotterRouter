# Infrastructure Tradeoffs and Operational Decisions

## Overview

Every infrastructure setup involves balancing performance, operational cost, setup complexity, and developer productivity. This document reviews key engineering decisions made when designing the SpotterRouter containerized stack.

---

## 1. Self-Hosted PostGIS vs Managed Cloud Database

### The Choice
Run PostgreSQL 16 with PostGIS 3.4 in a local Docker container using persistent disk volumes, rather than connecting to a managed cloud database such as AWS RDS or Neon.

### Why This Was Chosen
- Zero Network Latency: Spatial queries using `ST_DWithin` and `ST_LineLocatePoint` against 8,000+ stations run locally in under 15 milliseconds without round-trip network hops over the internet.
- Zero Cloud Cost: The entire test suite and development stack runs 100% offline on any laptop without needing cloud account credentials or monthly bills.
- Full Feature Support: All necessary spatial functions, GiST indexing, and geometry types are pre-installed in the PostGIS Docker image.

### Tradeoff
In a large enterprise production environment, managed databases provide automated nightly backups, cross-region replication, and point-in-time recovery. For this assessment and a single-VPS Dokploy deployment, running PostgreSQL in a container with a mounted volume is simpler, faster, and reliable.

---

## 2. Containerized OSRM vs External Routing APIs

### The Choice
Run a local Open Source Routing Machine (OSRM) container with a pre-built road network graph rather than calling external commercial APIs such as Google Directions or Mapbox.

### Why This Was Chosen
- Unlimited Requests: Commercial routing APIs charge between $5 to $10 per 1,000 requests and enforce strict rate limits. Self-hosted OSRM allows running hundreds of test suites and route searches without quota concerns.
- Offline Capability: Tests and development work anywhere, even without an active internet connection.
- High Throughput: OSRM calculates full cross-country road coordinates in 10 to 40 milliseconds.

### Tradeoff
OSRM requires sufficient RAM (around 1 GB for regional extracts) and an initial pre-processing step to build routing tables. Commercial APIs offer live traffic congestion data, which OSRM does not provide without real-time speed overlay feeds.

---

## 3. Redis Standalone vs Distributed Cache Cluster

### The Choice
Run a single Redis 7 container serving as both the route cache and the Celery message broker.

### Why This Was Chosen
- Minimal Operational Overhead: One container handles both caching and task queuing without configuring separate RabbitMQ and Redis clusters.
- Low Resource Footprint: Standalone Redis consumes under 30 MB of RAM at idle.
- Sufficient Throughput: A single Redis instance can easily handle tens of thousands of operations per second, which far exceeds the demands of this application.

### Tradeoff
A standalone Redis instance does not provide automatic master-replica failover. If the container stops, active background tasks pause until it restarts. As explained in the caching architecture docs, the application gracefully degrades to database queries if Redis is temporarily unreachable.

---

## 4. Multi-Container Compose vs Single Monolithic Container

### The Choice
Split services into separate containers (`backend`, `worker`, `db`, `redis`, `osrm`, `nginx`) rather than packing everything into a single all-in-one container image.

### Why This Was Chosen
- Independent Scaling: In production, worker containers can be scaled up independently to process AI explanation queues without altering web server capacity.
- Clean Failure Isolation: A memory spike in Celery or a crash in OSRM does not bring down the database or web server.
- Standard Industry Practice: Matches the deployment model used in Kubernetes, AWS ECS, and Dokploy.

### Tradeoff
Requires Docker Compose orchestration and internal network DNS configuration, which is handled cleanly through `docker-compose.base.yml`.
