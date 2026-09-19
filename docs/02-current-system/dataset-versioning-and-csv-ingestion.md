# Dataset Versioning and CSV Ingestion

## The Operational Challenge
In commercial logistics, diesel fuel prices change daily. An OPIS feed update contains new retail prices across tens of thousands of gas stations.
If an ingestion pipeline truncates or deletes the old database table while inserting the new CSV, any driver or API querying a route during that 2-minute window will receive errors. Furthermore, if the CSV contains malformed rows, the system could be left with corrupted data.

We designed a zero-downtime, version-controlled ingestion pipeline.

```text
[New OPIS CSV Upload]
         |
         v
+-----------------------+
|  Step 1: Validate     | ---> Checks columns: OPIS ID, Name, Address, City, State, Rack Price
+-----------------------+
         |
         v
+-----------------------+
|  Step 2: Geocoding    | ---> Zip code SQLite fallback database resolves lat/lng
+-----------------------+
         |
         v
+-----------------------+
|  Step 3: Hash Record  | ---> Computes SHA-256 fingerprint of file contents
+-----------------------+
         |
         v
+-----------------------+
|  Step 4: Atomic Write | ---> Creates PricingDataset record; inserts station batch
+-----------------------+
         |
         v
+-----------------------+
|  Step 5: Switch Active| ---> Sets is_active=True on new dataset; disables old
+-----------------------+
```

## How the Ingestion Pipeline Works

### 1. Ingestion via Web UI or CLI Command
Datasets can be loaded either through the web interface at `/datasets/` or via the automated management command:
```bash
python manage.py load_fuel_stations --file dataset/fuel-prices-for-be-assessment.csv --dataset-name "OPIS-SEPT-2026"
```

### 2. Fast Geocoding with Local SQLite
The original raw OPIS CSV provided city, state, and zip code, but lacked precise GPS coordinates (latitude and longitude). Making tens of thousands of live network calls to Google Maps or Nominatim would take hours and trigger rate limits.
We embedded `uszipcode` with an offline pre-cached SQLite database inside the Docker image. Geocoding 80,000 station locations runs locally in under 30 seconds with 100% offline reliability.

### 3. SHA-256 Checksum Integrity
Every uploaded dataset is hashed using SHA-256. If a dispatcher accidentally re-uploads the exact same CSV twice, the ingestion service detects the existing checksum and skips redundant database writes.

### 4. Zero-Downtime Dataset Activation
Each dataset record in `PricingDataset` has an `is_active` boolean:
- The new dataset is inserted into PostgreSQL with its own foreign key link (`dataset_id`).
- When the batch insertion is complete, a database transaction sets `is_active = True` on the new dataset and `is_active = False` on previous datasets.
- At no point is the database empty. Route queries running concurrently switch seamlessly to the new prices.

### 5. Instant Cache Invalidation
Because Redis cache keys incorporate the active dataset version hash:
```text
cache_key = f"trip:{dataset_hash}:{start_coords}:{end_coords}"
```
Activating a new dataset automatically invalidates all stale route caches without running expensive Redis scan-and-delete commands.
