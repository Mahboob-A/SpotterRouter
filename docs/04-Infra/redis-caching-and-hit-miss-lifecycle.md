# Redis Caching and Hit or Miss Lifecycle

## Overview

Calculating an optimal route across thousands of fuel stations requires geocoding origin and destination coordinates, calling the OSRM routing engine, performing PostGIS corridor searches, and running lookahead fuel math. Doing this on every single page view or API call would waste CPU cycles and degrade performance.

SpotterRouter uses a dedicated Redis container as an in-memory route cache to deliver sub-millisecond responses for previously calculated trips.

---

## Cache Key Derivation

Cache keys are generated deterministically using a SHA-256 hash of three components:

1. Normalized origin address (lowercased, whitespace-stripped).
2. Normalized destination address (lowercased, whitespace-stripped).
3. Active pricing dataset version code.

```
hashlib.sha256(f"{norm_start}::{norm_end}::{norm_version}".encode("utf-8")).hexdigest()
```

By including the active pricing dataset version code in the key, new fuel prices automatically invalidate old routes without requiring manual cache flush commands.

---

## The Hit or Miss Lifecycle

Every trip calculation and detail lookup follows a clear cache lifecycle:

### 1. First Time Calculation (Cache MISS)
When a user asks for a route that has not been computed before:
- The system checks Redis for the cache key. Nothing is found.
- The system computes the route using geocoding, OSRM, and the fuel optimization service.
- The plan is saved to PostgreSQL and serialized into Redis with a 24-hour time to live (TTL).
- The response returns an HTTP header: `X-Cache: MISS`.

### 2. Repeat Request Within 24 Hours (Cache HIT)
When a user or API client requests the exact same origin and destination while the key is still active in Redis:
- Redis finds the key and returns the serialized JSON plan in under 2 milliseconds.
- No geocoder, OSRM, or database query is executed.
- The system bumps the trip recency timestamp so it appears at the top of recent trips.
- The response returns an HTTP header: `X-Cache: HIT`.

### 3. User Recalculate Request (Cache MISS)
When a user clicks "Recalculate" on a trip detail page or sends `force_refresh: true` via the REST API:
- The cache lookup step is bypassed completely.
- A fresh route and optimization plan are recomputed against current stations.
- The existing record in PostgreSQL is updated with the new numbers and the Redis key is refreshed.
- The response returns an HTTP header: `X-Cache: MISS`.

### 4. Expired Cache (Cache MISS)
Keys in Redis are configured with a 24-hour expiration window (86,400 seconds). Once 24 hours pass:
- Redis drops the key automatically from memory.
- The next request sees that the key does not exist in the fast cache.
- The system treats this as a cache miss and returns `X-Cache: MISS`.

---

## Live Redis Inspection

To ensure the `X-Cache` HTTP header is accurate on direct URL visits, page reloads, and REST API calls, the system uses a dedicated inspection method:

```python
def exists_in_cache(self, cache_key: str) -> bool:
    if not cache_key:
        return False
    try:
        client = self._get_redis()
        if client is not None:
            return bool(client.exists(f"{self._redis_prefix}{cache_key}"))
    except (redis.RedisError, Exception):
        return False
    return False
```

This method directly queries Redis without falling back to PostgreSQL. If the key exists in Redis memory, the request reports `HIT`. If the key expired or was evicted, it reports `MISS`.

---

## Error Handling and Graceful Fallback

If the Redis container restarts or runs out of memory, the application does not crash or return HTTP 500 errors. The `TripCacheManager` catches connection exceptions, logs a warning, and falls back to PostgreSQL persistence. The site continues operating normally with slightly higher latency until Redis recovers.
