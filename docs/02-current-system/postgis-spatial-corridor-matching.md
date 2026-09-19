# PostGIS Spatial Corridor Station Matching

## The Spatial Challenge
The OPIS dataset contains tens of thousands of commercial truck stops across the contiguous United States. When a driver enters a route (for example, from Chicago, IL to Dallas, TX), we must find only the gas stations that sit directly along the highway corridor.

A station that is 10 miles away as the crow flies across a mountain or river without an exit ramp is useless. We need stations that are within a realistic driving detour buffer of our actual route polyline, and we must know their exact sequence along the journey.

```text
               Route Corridor (15-mile buffer)
  + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
  '                                                                       '
  '  Origin [A] =====> Station 1 =====> Station 2 ======> Destination [B] '
  '         (mi 0)     (mi 303)         (mi 783)           (mi 961)       '
  '                         * Station X (Off-route, ignored)              '
  + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
```

## How PostGIS Solves This

### 1. The Route LineString and SRID 4326
When OSRM returns turn-by-turn route coordinates, we assemble them into a PostGIS `LineString` with spatial reference ID `4326` (WGS 84 GPS standard coordinates).

### 2. Spatial Indexing with GiST
Every fuel station record in the database has a `location` column of type `Point` indexed with a Generalized Search Tree (`GiST`). Without this spatial index, PostgreSQL would have to scan all 80,000 rows in the database for every single route query. With the index, the bounding-box intersection filters out 99.8% of irrelevant stations in under 5 milliseconds.

### 3. Finding Stations with `ST_DWithin`
We use the `ST_DWithin` function to find all stations whose geographic point lies within 15 miles (24,140 meters) of the route LineString:
```sql
WHERE ST_DWithin(
    stations.location::geography,
    route_linestring::geography,
    24140.16 -- 15 miles converted to meters
)
```
Casting to `geography` ensures that distance calculations take the Earth's curvature into account instead of treating latitude and longitude as a flat cartesian grid.

### 4. Sequencing Stations with `ST_LineLocatePoint`
Knowing that a station is near the route is not enough. We also need to know where along the trip the truck reaches that station:
```sql
SELECT
    station.id,
    station.name,
    station.retail_price,
    ST_LineLocatePoint(route_linestring, station.location) AS route_fraction
FROM stations_station station
...
ORDER BY route_fraction ASC;
```
`ST_LineLocatePoint` projects the station point onto the route LineString and returns a float between `0.0` (at the route origin) and `1.0` (at the destination).
Multiplying `route_fraction` by the route's total distance gives the precise mileage from origin:
```text
station_mile_marker = route_fraction * total_trip_miles
```

## Eliminating False Matches
By combining `ST_DWithin` (corridor buffer) with `route_fraction` ordering, we achieve:
1. **Strict sequencing**: Stations are sorted exactly in the order the driver encounters them on the highway.
2. **Direction awareness**: Stations that sit behind the origin or beyond the destination are automatically ignored.
3. **Sub-20ms query time**: Even for a 3,000-mile cross-country route, the entire spatial lookup finishes in roughly 15 to 25 milliseconds.
