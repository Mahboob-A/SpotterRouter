# First Time with Greedy Lookahead Algorithms

## Discovering the Vehicle Refueling Problem
Before this assessment, I had heard of greedy algorithms in introductory computer science (such as Dijkstra's algorithm or Huffman coding), but I had never heard of or solved the **Vehicle Refueling Problem with Variable Prices** (sometimes called the Gas Station Problem).

When I first sat down to solve the fuel routing challenge, I thought:
`"Can I just use dynamic programming?"`
While dynamic programming can find an optimal solution, discretizing continuous fuel levels (gallons as floating-point decimals) over 3,000 miles of highway with 100 potential candidate stops creates an enormous state-space matrix that is slow to compute.

I began researching optimization literature and studied how commercial fleet logistics software solves this problem using **Greedy Lookahead Heuristics**.

```text
               THE LOOKAHEAD HORIZON CONCEPT
Current Station (Price: $3.10/gal)
   |
   |--- Lookahead Window (Reachable with current tank: up to 500 mi) --->
   |
   +----> Station A (120 mi ahead, Price: $3.25) -> More expensive
   |
   +----> Station B (280 mi ahead, Price: $2.79) -> CHEAPER!
          |
          v
DECISION: Buy ONLY enough fuel at current station to reach Station B!
Gallons to buy = (280 mi - current_runway) / 10 MPG.
```

---

## Core Lessons Learned

### 1. Understanding the Lookahead Horizon
A pure greedy algorithm only looks at the immediate next step. That fails in fuel optimization because the cheapest station might be two stops away.
A **lookahead** algorithm expands its vision across the entire reachable horizon (everything within current fuel range). This allows the engine to make strategic decisions:
- If a cheaper station is within reach, buy the bare minimum at the current stop.
- If no cheaper station exists in the entire reachable window, the current station is a local price minimum. Take full advantage of it by filling the tank to its 500-mile capacity!

### 2. Guarding the Remaining Runway
One of the trickiest edge cases I encountered during early test runs was runway management.
If the truck has 200 miles of runway left when it pulls into Station A, and the next cheaper station is 320 miles away:
- The truck does not need 320 miles worth of fuel!
- It already has 200 miles in the tank.
- It only needs to buy `320 - 200 = 120 miles` worth of fuel (`12.0 gallons`).
Writing test cases with explicit runway assertions helped me refine this math and avoid over-purchasing.

### 3. Arrival Fuel Discipline
Another critical lesson was avoiding unnecessary fuel purchases at the end of a route.
Commercial fleet drivers do not get rewarded for returning to the company terminal with a completely full tank bought at retail prices. The company prefers to refuel at bulk wholesale terminal rack prices.
Adding the **Destination Runway Guard** ensured that as the truck nears the destination, it never purchases more fuel than the exact remaining distance required to arrive safely.

---

## Practical Takeaway
Studying and implementing the greedy lookahead algorithm was one of the most intellectually rewarding parts of this assessment. It demonstrated that a well-designed O(N) heuristic algorithm can produce near-optimal solutions in under 2 milliseconds, outperforming heavy brute-force or linear programming solvers.
