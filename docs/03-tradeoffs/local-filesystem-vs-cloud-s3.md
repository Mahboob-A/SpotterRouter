# Local Filesystem vs Cloud S3 Storage

## The Context of the Decision
In commercial production systems, user-uploaded files (like price CSVs) and generated media (like PDF dispatch documents or route maps) are almost always offloaded to object storage services like Amazon Web Services S3 or Google Cloud Storage.

For this technical assessment, I chose an in-memory and local filesystem architecture. This document explains why this decision was made for the demo and how the production system transitions to cloud object storage.

```text
               DEMO ARCHITECTURE (Current Implementation)
  +-----------------------------------------------------------------+
  |  [User] ===> [Django Gunicorn Worker]                           |
  |                    |                                            |
  |                    +---> CSV upload: Stored in /app/dataset/    |
  |                    |                                            |
  |                    +---> PDF export: Streamed in-memory (0 disk)|
  +-----------------------------------------------------------------+

               PRODUCTION ARCHITECTURE (Cloud Scaled)
  +-----------------------------------------------------------------+
  |  [User] ===> [CloudFront CDN] ===> [Django Application Cluster] |
  |                                                  |              |
  |  [S3 Upload Bucket] <--- Presigned URL <---------+              |
  |  [S3 Reports Bucket]<--- Background Worker Worker Store         |
  +-----------------------------------------------------------------+
```

## Why Local and In-Memory Storage for the Assessment

### 1. Zero External Cloud Friction
If the assessment required AWS credentials, S3 bucket names, and IAM policies, anyone reviewing or evaluating this project locally would have to set up their own AWS account, create buckets, and configure environment variables just to run `make up` and test the application.
By making the assessment self-contained within Docker Compose, a reviewer can clone the repository, run `make up`, and immediately test CSV uploads and PDF exports with zero configuration hurdles.

### 2. Eliminating Disk Growth with Memory Streaming
Generating PDF dispatch sheets in memory using Python's `io.BytesIO` buffer means the container does not accumulate temporary files on disk. Every PDF is built in RAM, transmitted over HTTP, and garbage-collected immediately.

### 3. Local Volume Mounts for Rapid Development
In `docker-compose.dev.yml`, the local `dataset/` folder is mounted into the container. This allows instant testing of new sample CSV files directly from the host machine without rebuilding the Docker container.

## How Production Scales to AWS S3

When deploying this system to handle millions of commercial freight trips, the architecture evolves cleanly without touching core business logic:

1. **Pre-Signed Upload URLs**:
   Dispatchers uploading multi-gigabyte OPIS CSV files upload directly from their browser to an S3 ingestion bucket using pre-signed PUT URLs. This avoids tying up Django Gunicorn workers with large file uploads.
2. **Event-Driven Ingestion**:
   An S3 `ObjectCreated` event triggers an AWS SQS queue or Celery task to parse and ingest the CSV asynchronously.
3. **Dispatch PDF Archival**:
   Generated PDF dispatch sheets are saved to an S3 reports bucket with an automated 30-day lifecycle rule. The user receives a pre-signed CloudFront CDN URL with caching.
4. **Adapter Interface**:
   Because file handling in SpotterRouter is abstracted behind service classes (`DatasetIngestionService` and `TripPdfReportService`), switching the storage backend from local disk to S3 requires only updating the storage adapter class, leaving the domain and UI code unchanged.
