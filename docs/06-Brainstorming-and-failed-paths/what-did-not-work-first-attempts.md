# What Did Not Work - First Attempts and Failed Paths

## Engineering Honesty in Problem Solving
Building a production-grade route optimizer is rarely a straight line. Many initial ideas that sounded reasonable on paper failed when tested against real geographical data, real truck ranges, and interstate highway networks.

This document outlines four key approaches that were attempted, why they failed, and what was learned from those failures.

```text
FAILED PATH 1: Fixed Midpoint Stops
[Origin] ======= [Stop: Exactly 450 mi] ======= [Stop: Exactly 900 mi] ======> [Destination]
Problem: Gas stations do not exist at arbitrary mathematical coordinates in rural deserts!

FAILED PATH 2: Bounding-Box Spatial Filtering
[Origin] +---------------------------------------------------------+ [Destination]
         | Bounding Box matches stations 200 miles off-interstate   |
         +---------------------------------------------------------+
Problem: Matches stations across mountain ranges without highway access.

FAILED PATH 3: Full-Tank Refueling at Every Stop
Problem: Wastes money when a much cheaper station is 50 miles ahead across a state border.

FAILED PATH 4: Volunteer OpenStreetMap Tile URLs
Problem: Triggers automated HTTP 403 blocks due to OSM server bandwidth policies.
```

---

## Failed Attempt 1: Fixed Midpoint Mathematical Stops

### The Concept:
Divide the trip distance by 450 miles (to stay comfortably under the 500-mile tank limit) and search for the closest station to mile marker 450, 900, 1350, etc.

### Why It Failed:
- Highways do not have gas stations evenly spaced at mathematical intervals. In western states like Wyoming, Nevada, and New Mexico, there can be stretches of 90 miles with zero commercial truck stops.
- If mile marker 450 lands in the middle of a national park or desert, the nearest station might be at mile 410 or mile 515. Forcing a stop at mile 450 causes the truck to run out of fuel or make an unnecessary detour.
- It completely ignores fuel price differentials. A station at mile 380 might charge $2.75/gal while the station at mile 450 charges $3.89/gal.

---

## Failed Attempt 2: Bounding-Box Spatial Filtering

### The Concept:
Create a rectangular geographic bounding box (`ST_MakeEnvelope`) between the origin and destination coordinates and find all stations inside that rectangle.

### Why It Failed:
- Real highway corridors curve dramatically. A route from Seattle, WA to Salt Lake City, UT curves through Idaho. A simple bounding box encompasses thousands of square miles of wilderness, mountain ranges, and local roads that the truck will never travel on.
- The query returned over 8,000 irrelevant stations, overwhelming Python's memory and slowing the calculation down to over 3 seconds.
- **The Fix**: Abandoned rectangular bounding boxes in favor of `ST_DWithin` with a 15-mile buffer directly along the route's actual driving LineString.

---

## Failed Attempt 3: Always Refueling to Full (100% Tank)

### The Concept:
Whenever the truck pulls into a designated fuel stop, always pump fuel until the 50-gallon tank is completely full.

### Why It Failed:
- Consider a truck traveling through Missouri (average diesel price: $2.82) toward Oklahoma (average diesel price: $2.55).
- If the truck stops in southern Missouri with 100 miles of runway remaining and buys 40 gallons at $2.82 to fill the tank to 500 miles, it wastes money.
- The optimal strategy is to purchase *only* enough fuel (about 12 gallons) to safely reach the cheaper Oklahoma station, where the full tank can be filled at $2.55/gal.
- **The Fix**: Greedy lookahead horizon logic that adjusts gallon purchases based on upcoming prices.

---

## Failed Attempt 4: Direct Volunteer OSM Map Tiles

### The Concept:
Use standard `https://tile.openstreetmap.org/{z}/{x}/{y}.png` in Leaflet.js without an external tile provider account.

### Why It Failed:
- As soon as concurrent requests hit the map, the OpenStreetMap Foundation's automated firewalls blocked the requests with HTTP `403 Forbidden` errors.
- Volunteer servers are not permitted for commercial application use or heavy automated testing.
- **The Fix**: Integrated MapTiler Cloud Streets v2 raster tiles with proper API key configuration and an environment variable fallback mechanism.
