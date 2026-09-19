# Learning the USA Freight and Fuel Ecosystem

## Stepping Outside the Software Bubble
Building software for logistics requires understanding the physical domain. Before this assessment, my knowledge of long-haul trucking was limited to seeing semi-trucks on the highway.
To build an accurate fuel routing system, I had to educate myself on how commercial freight operations actually function across the United States.

```text
                  THE CLASS 8 TRUCK ECOSYSTEM
+-----------------------------------------------------------------+
|  Vehicle Type: Class 8 Heavy-Duty Tractor-Trailer               |
|  Gross Vehicle Weight Rating (GVWR): Over 33,000 lbs (up to 80k)|
|  Standard Fuel: Ultra-Low Sulfur Diesel (ULSD)                  |
|  Dual Fuel Tanks: 100 to 150 gallons each (total 200 - 300 gal) |
|  Fuel Economy: ~6.5 to 10.0 Miles Per Gallon (Assessment = 10)  |
|  Safe Operational Leg: 400 - 500 miles between refuels          |
|  Pricing Benchmark: OPIS (Oil Price Information Service)       |
+-----------------------------------------------------------------+
```

---

## What I Learned About the Industry

### 1. Dual Fuel Tanks and Safe Range
Commercial semi-trucks rarely have a single small gas tank. Most modern tractors feature dual cylindrical aluminum tanks mounted on either side of the chassis, holding between 100 and 150 gallons each.
While a truck could theoretically travel 1,500 miles on completely full 300-gallon dual tanks, fleet managers enforce a **450 to 500-mile safe operational leg**.
Why?
- **Department of Transportation (DOT) Hours of Service (HOS)**: Drivers are legally required to take safety rest breaks after several hours of driving. Refueling happens naturally during mandatory driver breaks.
- **Weight and Payload Limits**: Diesel fuel weighs approximately 7.1 pounds per gallon. Carrying 250 unnecessary gallons adds 1,775 pounds of dead weight, which reduces the amount of revenue-generating cargo the truck can legally carry under the 80,000-lb federal gross weight limit!

### 2. State Fuel Tax Differentials
Diesel prices vary significantly between US states because of state excise taxes and environmental surcharges.
For example:
- A state with high fuel excise taxes (such as Pennsylvania or California) might have diesel priced at $4.20 per gallon.
- A neighboring state (such as Ohio or Missouri) might have diesel priced at $2.85 per gallon.
A long-haul truck buying 100 gallons across the state line can save over $130 on a single fill-up. Multiply that across a fleet of 500 trucks running cross-country routes weekly, and smart fuel routing saves millions of dollars annually.

### 3. What is OPIS?
The assessment dataset is labeled `fuel-prices-for-be-assessment.csv` and contains fields from **OPIS** (Oil Price Information Service).
OPIS is the premier pricing benchmark for the US petroleum industry. In commercial trucking, fleets negotiate discounted contracts with major truck stop networks (such as Pilot Flying J, Love's Travel Stops, and TA-Petro) based on OPIS rack wholesale prices plus a fixed pumping fee.
Understanding that these prices reflect commercial diesel pricing helped me ensure our fuel cost metrics and currency rounding matched real freight billing standards.
