# Asynchronous Celery Worker Pipeline

## Why Not Run Everything in the Web Request?
When a driver or fleet manager requests a route, they need the core navigation data immediately:
- The total mileage.
- The recommended gas station stops.
- The gallons of fuel to buy at each stop.
- The interactive map showing the route line and markers.

Generating an AI explanation using large language models (such as DeepSeek via Fireworks AI) takes anywhere from 2 to 8 seconds depending on model load and network latency. If we blocked the Django HTTP request until the AI responded, the user would stare at a frozen browser screen thinking the app crashed.

```text
[Browser] --- (1) POST / ---+
                            |
                            v
                   +------------------+
                   |  Django Backend  |
                   +--------+---------+
                            |
         +------------------+------------------+
         |                                     |
         v                                     v
(2) Compute Fuel Route (Fast)        (3) Queue AI Explanation Task
         |                                     |
         v                                     v
(4) Redirect to /trips/<uuid>/           [Redis Broker]
         |                                     |
         v                                     v
(5) Page Loads Immediately (<100ms)    +---------------------+
         |                             | Celery Worker Task  |
         |                             +----------+----------+
         |                                        |
         | (6) Polls for explanation status       v
         +<-------------------------- (7) Calls Fireworks LLM
                                                  |
                                                  v
                                       (8) Saves result to DB
```

## How the Asynchronous Pipeline Operates

### 1. Fast Route Generation and Redirection
The Django web request executes only the deterministic calculations:
- Coordinates are geocoded.
- Turn-by-turn road geometry is fetched from OSRM.
- Candidate fuel stations are filtered in PostGIS.
- The greedy lookahead fuel algorithm computes the stops.
- The `TripPlan` is saved to PostgreSQL with `explanation_status = "PENDING"`.
- A Celery task `generate_ai_explanation.delay(str(trip.id))` is dispatched to Redis.
- The user is immediately redirected to `/trips/<uuid>/`. Total user wait time is under 150 milliseconds.

### 2. Celery Worker Execution
In the background, a dedicated Celery worker container picks up the task from Redis:
- It fetches the trip plan and fuel stops from PostgreSQL.
- It formats a concise prompt detailing the route distance, chosen fuel stops, and price differentials.
- It calls the Fireworks AI API using the DeepSeek model.
- Upon receiving the explanation text, it updates the `TripPlan` record with `explanation_status = "COMPLETED"` and the explanation body.

### 3. Frontend Polling and Smooth Degradation
On the trip detail page, a small JavaScript polling loop checks the status endpoint every 2 seconds:
- While pending, the UI displays a clean pulsating badge: "Analyzing fuel economics...".
- When the task completes, the card smoothly updates with the AI text without any page reload.
- If the AI task fails, times out, or if the API key is not configured, the worker marks `explanation_status = "FAILED"`.
- The frontend detects this and displays a deterministic fallback explanation based on the calculated numbers, ensuring the user always sees a helpful summary.

## Operational Resilience
- **Decoupled Scaling**: Web workers (Gunicorn) and background workers (Celery) run in isolated containers. A burst of route calculations will not starve the web server of threads.
- **Fail-Safe Tasks**: If Redis restarts, unacknowledged tasks are re-queued automatically.
- **Strict Timeouts**: The LLM HTTP client has a strict 10-second connection and read timeout. Workers never hang indefinitely.
