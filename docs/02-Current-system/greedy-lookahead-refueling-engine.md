# Greedy Lookahead Refueling Engine

## The Problem Statement
A commercial Class 8 semi-truck departs with a full tank of fuel. The problem specification defines:
- **Maximum Vehicle Range**: 500 miles.
- **Fuel Economy**: 10 miles per gallon (MPG).
- **Tank Capacity**: 500 miles / 10 MPG = 50.0 gallons.
- **Initial Fuel Runway**: 500 miles (full 50 gallons).

The truck must reach its destination safely without ever letting the fuel tank drop below zero. Along the route, diesel fuel prices vary drastically between states and individual truck stops (often varying by $0.50 to $1.20 per gallon).

Our goal is simple: **Minimize total fuel expenditure for the entire trip.**

```text
Mile 0                      Mile 303               Mile 783           Mile 961
[Origin] =================> [Stop #1: $2.92] ======> [Stop #2: $2.85] => [Destination]
Runway: 500 mi              Runway: 197 mi         Runway: 100 mi
                           Buy 28.3 gal            Buy 14.2 gal
```

## Why Simple Heuristics Fail
- **Naive approach 1 (Refuel when empty)**: Running the tank down to 10 miles and stopping at whatever station happens to be there forces you to buy expensive fuel if that station charges $3.89/gal while a station 40 miles earlier charged $2.85/gal.
- **Naive approach 2 (Always fill to full)**: If you stop at a station charging $3.10/gal and fill the tank completely, you waste money if another station 90 miles ahead charges $2.65/gal. You should only buy enough fuel at the more expensive stop to reach the cheaper stop.

## How the Greedy Lookahead Engine Works

### Step 1: Track the Remaining Runway
At each decision point (starting at mile 0), the truck has a current runway (in miles) and current fuel in gallons (`runway / 10.0`).

### Step 2: Determine Reachable Stations
From the current position, the algorithm looks at all candidate stations that can be reached with the fuel currently in the tank (`station_miles <= current_miles + current_runway`).

### Step 3: Scan Ahead for Cheaper Fuel
Within the reachable window, the algorithm checks if there is any station cheaper than the current station:
- **Case A: A cheaper station exists ahead**:
  The algorithm refuels at the current stop with *only* enough gallons to reach that cheaper station. Why buy expensive fuel when cheaper fuel is within reach?
- **Case B: No cheaper station exists ahead**:
  The current station is the cheapest option in the reachable horizon. The algorithm fills the tank up to the maximum capacity (500 miles runway) to maximize the amount of cheap fuel carried forward.

### Step 4: Destination Runway Guard
When approaching the destination, the truck only needs enough fuel to cross the finish line. The algorithm caps the purchase so that `current_runway + purchase_runway` never exceeds the remaining distance to the destination (plus a small safety buffer). Drivers do not spend company capital buying surplus fuel to leave in the destination parking lot.

## Concrete Example: Marion, IL to Wilmer, TX

| Stop | Station Name | Mile | Price / Gal | Gallons Purchased | Stop Cost | Action Reason |
|---|---|---|---|---|---|---|
| Origin | Chicago, IL | 0.0 mi | - | 0.000 gal (Starts Full) | $0.00 | 500 mi initial runway |
| #1 | HUCKS FOOD & FUEL | 303.7 mi | $2.929 | 28.334 gal | $82.99 | Tops runway to reach Texas corridor |
| #2 | Quiktrip #7900 | 783.3 mi | $2.857 | 1.259 gal | $3.60 | Reaches cheaper stop 12 miles ahead |
| #3 | EXTRA MILE STOP | 795.9 mi | $2.817 | 12.994 gal | $36.60 | Cheaper fuel, extends runway |
| #4 | CADDO MILLS | 925.8 mi | $2.801 | 3.558 gal | $9.97 | Minor top-off before final stretch |
| #5 | One9 #1248 | 961.4 mi | $2.756 | 0.700 gal | $1.93 | Final stop at cheapest price |
| Total | - | 961.4 mi | - | 46.845 gal | $135.09 | Full route completed safely |

Notice the math:
- Total trip length: 961.4 miles.
- Fuel required to cover 961.4 miles at 10 MPG: 96.14 gallons.
- Initial fuel in tank at departure: 50.00 gallons (covers 500 miles).
- Net fuel purchased: 46.845 gallons (covers 468.45 miles).
- Total fuel available: 50.00 + 46.845 = 96.845 gallons (covers 968.45 miles).
- Safety reserve remaining at destination: 7.05 miles runway.

The engine delivered optimal total cost without running dry or over-purchasing surplus diesel.
