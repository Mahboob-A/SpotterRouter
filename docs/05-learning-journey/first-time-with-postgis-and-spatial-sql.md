# First Time with PostGIS and Spatial SQL

## An Honest Starting Point
Before taking on this assessment, I had never worked with PostGIS or written spatial SQL queries. My background with databases primarily involved standard relational schemas: primary keys, foreign keys, indexes, and B-Tree lookups.

When I read the assessment requirement:
`"Find fuel stations along a route corridor within 500 miles max vehicle range across the USA"`, I realized traditional SQL queries like `WHERE lat BETWEEN ... AND lng BETWEEN ...` would not cut it. I needed to dive into spatial databases.

```text
               WHAT I LEARNED ABOUT SPATIAL DATA
+---------------------------------------------------------------+
|  1. Coordinates are not flat Cartesian numbers.               |
|     1 degree of longitude at the equator != 1 degree in Ohio! |
+---------------------------------------------------------------+
|  2. SRID 4326 is the universal GPS standard (WGS 84).         |
|     (Longitude comes first in GIS geometries: Point(lng lat))  |
+---------------------------------------------------------------+
|  3. Geography vs Geometry types:                              |
|     - Geometry = Flat plane math (degrees)                    |
|     - Geography = Spherical earth math (meters on spheroid)   |
+---------------------------------------------------------------+
|  4. GiST indexing accelerates 80,000 point scans to < 5ms.    |
+---------------------------------------------------------------+
```

---

## Key Concepts Discovered and Mastered

### 1. The Geography vs Geometry Distinction
My first spatial query ran `ST_DWithin(station.location, route, 15)`. The query failed or returned completely nonsensical results because I passed `15` thinking it meant 15 miles!
In PostGIS:
- If your column is `geometry(Point, 4326)`, the distance unit is in **degrees**. A distance of 15 degrees is roughly 1,000 miles!
- To measure distances in real-world meters or miles, you must cast to `geography`:
  ```sql
  ST_DWithin(station.location::geography, route_geom::geography, 24140.16)
  ```
  `24,140.16` meters equals exactly 15 statute miles calculated over the WGS 84 ellipsoid.

### 2. Point Coordinate Order: (Longitude, Latitude)
In general conversation, humans say "Latitude, Longitude" (e.g. `34.05, -118.25`).
However, in mathematics, GIS, GeoJSON, and PostGIS, coordinates follow standard Cartesian `(X, Y)` conventions:
- `X` represents horizontal displacement (Longitude: East/West, between -180 and +180).
- `Y` represents vertical displacement (Latitude: North/South, between -90 and +90).
Passing coordinates in reverse order places points in Antarctica or the Indian Ocean! Adopting strict type definitions (`RouteCoordinate(lng=..., lat=...)`) eliminated this mistake permanently.

### 3. Projecting Points with `ST_LineLocatePoint`
The breakthrough moment for sorting fuel stations along the route came from discovering `ST_LineLocatePoint`.
Given a 3D or 2D LineString with thousands of turn-by-turn road coordinates, `ST_LineLocatePoint(line, point)` drops a perpendicular line from the station onto the route and calculates the exact fraction along the line (from 0.0 to 1.0).
This allowed me to order stations along a 2,500-mile highway in exact travel sequence with a single SQL query.

---

## Reflections on Spatial Engineering
Learning PostGIS for this project was challenging but rewarding. Working directly with spatial C extensions (GEOS, GDAL, and Proj) inside Docker and seeing 80,000 station records queried in under 20 milliseconds gave me a deep appreciation for the power of spatial databases in real-world logistics applications.
