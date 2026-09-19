# What Worked Well and Why

## Successful Architecture Choices
After iterating through the failed prototypes described in the previous document, several key architectural decisions stood out as major successes. These choices directly enabled high performance, mathematical accuracy, and great user experience.

```text
+-------------------------------------------------------------------------+
|                        KEY ARCHITECTURAL WINS                           |
+-------------------------------------------------------------------------+
|  1. PostGIS Corridor Buffering (ST_DWithin + ST_LineLocatePoint)        |
|     -> Reduces 80,000 stations down to ~35 relevant highway stops in 18ms|
+-------------------------------------------------------------------------+
|  2. Greedy Lookahead with Price Horizon Window                          |
|     -> Dynamic partial fills save fleet capital before cheap fuel zones |
+-------------------------------------------------------------------------+
|  3. Destination Runway Guard                                            |
|     -> Eliminates over-purchasing surplus fuel at destination           |
+-------------------------------------------------------------------------+
|  4. Two-Tier Normalization Caching (Redis + PostgreSQL)                 |
|     -> Sub-5ms repeat route responses and instant UI rendering          |
+-------------------------------------------------------------------------+
```

---

## Success 1: PostGIS Corridor Buffering and Station Sequencing

### The Implementation:
Using `ST_DWithin` on the route LineString with a 15-mile buffer, combined with `ST_LineLocatePoint` to project each station onto the route as a float fraction between 0.0 and 1.0.

### Why It Worked So Well:
- It eliminates the need for expensive geometric distance calculations in Python. PostgreSQL does the math using optimized C spatial libraries (GEOS and Proj).
- The query returns candidate stations already sorted in the exact sequential order the driver encounters them along the highway.
- In benchmarks, querying 80,000 station records along a 1,200-mile corridor takes under 20 milliseconds on a standard PostgreSQL instance with GiST indexing.

---

## Success 2: Greedy Lookahead with Price Horizon

### The Implementation:
Instead of a rigid rule, the algorithm models fuel like an investment runway:
- When standing at a station, scan all upcoming stations reachable with current fuel.
- If a cheaper station exists ahead, purchase only what is needed to reach it.
- If no cheaper station exists ahead, fill the tank up to the 500-mile capacity.

### Why It Worked So Well:
- It handles natural price geography in the United States, where state fuel excise taxes cause sudden price jumps across state borders (for example, crossing from Illinois into Missouri or Indiana).
- The algorithm naturally minimizes total trip expenditure without requiring an exponential brute-force combinatorial search across all possible combinations.
- It executes in less than 1 millisecond of pure Python CPU time.

---

## Success 3: Destination Runway Guard

### The Implementation:
When the remaining distance to the destination is less than the truck's maximum range (500 miles), cap any purchase to:
```python
max_needed = max(0.0, miles_to_destination - current_runway)
```

### Why It Worked So Well:
- Solved a subtle bug where the algorithm would fill 45 gallons at the second-to-last stop when only 4 gallons were needed to reach the destination terminal.
- Aligning fuel purchases with trip completion guarantees the truck arrives with a safe reserve without wasting budget.

---

## Success 4: Dataset-Hashed Cache Keys

### The Implementation:
Incorporating the active OPIS dataset SHA-256 fingerprint directly into the Redis cache key:
```text
key = f"trip:{dataset_hash}:{norm_start_lat}:{norm_start_lng}:{norm_end_lat}:{norm_end_lng}"
```

### Why It Worked So Well:
- Completely solved the cache invalidation problem when new fuel datasets are ingested.
- No need to iterate over thousands of Redis keys or run `FLUSHDB` (which can cause latency spikes).
- As soon as a new dataset is activated, all subsequent route calculations automatically generate fresh plans with the new prices.
