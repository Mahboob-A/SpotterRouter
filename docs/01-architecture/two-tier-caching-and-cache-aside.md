# Two-Tier Caching and Cache-Aside Pattern

## The Latency Challenge
Calculating long-haul commercial truck routes across the United States involves multiple network and computational steps:
1. Geocoding origin and destination addresses into latitude and longitude coordinates.
2. Requesting the turn-by-turn road geometry and cumulative distance from the routing engine (OSRM).
3. Querying tens of thousands of fuel stations in PostGIS along the highway corridor.
4. Running the greedy lookahead optimization engine.

Without caching, a trip from New York, NY to Los Angeles, CA takes between 800 milliseconds and 2 seconds. Repeating that query with the exact same inputs should be instant.

```text
[User Request: Start -> End]
           |
           v
+-----------------------+
|  Step 1: Check Redis  | ---> HIT ---> Return serialized route (< 5ms)
+-----------------------+
           |
         MISS
           v
+-----------------------+
|  Step 2: Check PostGIS| ---> HIT ---> Populate Redis & Return (< 15ms)
+-----------------------+
           |
         MISS
           v
+-----------------------+
|  Step 3: Compute Route| ---> Full calculation: OSRM + PostGIS + Engine
+-----------------------+
           |
           v
+-----------------------+
|  Step 4: Save & Cache | ---> Write to PostgreSQL and set Redis key (TTL 24h)
+-----------------------+
```

## Tier 1: In-Memory Fast Cache (Redis)
Redis serves as our Tier 1 cache. It stores computed trip responses in serialized JSON format with an explicit time-to-live (TTL):
- **Key Normalization**: Real-world users often type slightly different variations of coordinates or addresses (for example, `34.052234` vs `34.052201`). We round coordinates to 2 decimal places (roughly 1.1 km resolution) for the routing cache key.
- **Dataset Hashing**: When a fleet operator uploads a new OPIS fuel pricing dataset, all cached fuel prices from the old dataset become stale. To solve this without needing to flush the entire Redis database, we include the active dataset version hash inside the cache key:
  ```text
  cache_key = f"trip:{dataset_version_hash}:{norm_start_lat}:{norm_start_lng}:{norm_end_lat}:{norm_end_lng}"
  ```
  When the active dataset changes, old keys simply expire naturally or are bypassed immediately.

## Tier 2: Persistent Relational Cache (PostgreSQL / PostGIS)
PostgreSQL serves as our Tier 2 persistent cache:
- Every computed trip plan is stored in the `TripPlan` table, complete with its origin, destination, total miles, fuel cost, total gallons purchased, and the full GeoJSON polyline geometry.
- If Redis restarts or its memory fills up, the application checks the database for an existing identical trip plan before calling external routing APIs.
- Users can access their trips at any time via permalinks (`/trips/<uuid>/`) or download their driver dispatch PDF sheet.

## The Cache-Aside Flow
1. **Read Request**:
   - The application checks Redis for `cache_key`.
   - If present (cache hit), it returns the cached trip plan in under 5 milliseconds.
   - If missing (cache miss), the application checks PostgreSQL for a recent trip record with matching endpoints.
   - If PostgreSQL has it, the data is placed into Redis and returned.
   - If both miss, the application runs the full route calculation pipeline.
2. **Write Completion**:
   - The computed trip is saved transactionally to PostgreSQL.
   - The serialized plan is saved into Redis with a 24-hour expiration window.

## Real Performance Impact

| Metric | Fresh Cold Calculation | Tier 2 DB Hit | Tier 1 Redis Hit |
|---|---|---|---|
| Response Time | 850ms - 1,800ms | 15ms - 25ms | 2ms - 5ms |
| External API Calls | 1 OSRM call | 0 calls | 0 calls |
| PostGIS Spatial Work | Full ST_DWithin buffer | None | None |
| CPU Utilization | Moderate | Very Low | Negligible |
