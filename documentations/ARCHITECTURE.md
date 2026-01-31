# Docker Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Movie Recommendation System                     │
│                      Docker Deployment Architecture                 │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                          Build Pipeline                               │
└───────────────────────────────────────────────────────────────────────┘

    ./docker/build.sh
           ↓
    ┌──────────────────┐
    │  Dockerfile      │
    │  (Multi-Stage)   │
    └──────────────────┘
           ↓
    ┌──────────────────┐
    │  Stage 1:        │     System deps (gcc, g++, make)
    │  BUILDER         │  →  Python packages (numpy, pandas, etc.)
    │  (python:3.10)   │     Size: ~400MB
    └──────────────────┘
           ↓
    ┌──────────────────┐
    │  Stage 2:        │     Copy ml-100k/ + src/ + train_model.py
    │  TRAINING        │  →  Run: python train_model.py
    │  (from builder)  │     Output: models/v1.0.0/*.pkl
    └──────────────────┘     Size: ~450MB
           ↓
    ┌──────────────────────────────────┬─────────────────────────────┐
    │  Stage 3: SERVING                │  Stage 4: RETRAINING        │
    │  (python:3.10-slim)              │  (from builder)             │
    │  • Copy models/ from training    │  • Install cron             │
    │  • Copy api/ + src/              │  • Schedule: Sun 2 AM       │
    │  • Non-root user (recsys)        │  • Manual trigger support   │
    │  • Expose: 8000                  │                             │
    │  • Health check enabled          │                             │
    │  Size: ~500MB                    │  Size: ~420MB               │
    └──────────────────────────────────┴─────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────┐
│                     Runtime Architecture                              │
└───────────────────────────────────────────────────────────────────────┘

                        docker-compose up -d

    ┌─────────────────────────────────────────────────────────┐
    │                  Service: TRAINING                      │
    │  Container: recsys-training                             │
    │  Image: movie-recsys-training:latest                    │
    │  Restart: no (run once and exit)                        │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │ Volumes:                                        │    │
    │  │  • ./ml-100k → /app/ml-100k (ro)               │    │
    │  │  • model-artifacts → /app/models (rw)          │    │
    │  │  • training-logs → /app/logs (rw)              │    │
    │  └─────────────────────────────────────────────────┘    │
    │  Command: python train_model.py                         │
    │  Output: models/v1.0.0/*.pkl (~50MB)                    │
    └─────────────────────────────────────────────────────────┘
                            ↓ (depends_on)
    ┌─────────────────────────────────────────────────────────┐
    │                    Service: API                         │
    │  Container: recsys-api                                  │
    │  Image: movie-recsys-api:latest                         │
    │  Restart: unless-stopped                                │
    │  Port: 8000:8000                                        │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │ Volumes:                                        │    │
    │  │  • model-artifacts → /app/models (ro)          │    │
    │  │  • ./ml-100k → /app/ml-100k (ro)               │    │
    │  │  • api-logs → /app/logs (rw)                   │    │
    │  └─────────────────────────────────────────────────┘    │
    │  Workers: 4 (Uvicorn)                                   │
    │  Health check: GET /health (every 30s)                  │
    │  Endpoints: /recommend, /movies/*, /metrics, /docs      │
    └─────────────────────────────────────────────────────────┘
                            ↓ (shares volume)
    ┌─────────────────────────────────────────────────────────┐
    │                Service: RETRAINING                      │
    │  Container: recsys-retraining                           │
    │  Image: movie-recsys-retraining:latest                  │
    │  Restart: unless-stopped                                │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │ Volumes:                                        │    │
    │  │  • ./ml-100k → /app/ml-100k (ro)               │    │
    │  │  • model-artifacts → /app/models (rw)          │    │
    │  │  • retraining-logs → /app/logs (rw)            │    │
    │  └─────────────────────────────────────────────────┘    │
    │  Cron: 0 2 * * 0 (Sunday 2 AM)                          │
    │  Command: cron -f                                       │
    │  Manual: docker-compose run --rm retraining ...         │
    └─────────────────────────────────────────────────────────┘

                 ┌────────────────────────────┐
                 │  Docker Network:           │
                 │  recsys-network (bridge)   │
                 └────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────┐
│                   Development vs Production                           │
└───────────────────────────────────────────────────────────────────────┘

DEVELOPMENT (docker-compose.dev.yml)          PRODUCTION (docker-compose.yml)
─────────────────────────────────────────────────────────────────────────
./docker/start-dev.sh                         docker-compose up -d

┌────────────────────────────┐                ┌────────────────────────────┐
│ Training Service           │                │ Training Service           │
│ • RECSYS_ENVIRONMENT=dev   │                │ • RECSYS_ENVIRONMENT=prod  │
│ • Volume: ./src → /app/src │                │ • Code baked in image      │
│ • Volume: ./models (host)  │                │ • Volume: named volume     │
└────────────────────────────┘                └────────────────────────────┘

┌────────────────────────────┐                ┌────────────────────────────┐
│ API Service                │                │ API Service                │
│ • Live reload: TRUE        │                │ • Live reload: FALSE       │
│ • Workers: 1               │                │ • Workers: 4               │
│ • Volume mounts:           │                │ • Code baked in image      │
│   - ./src → /app/src       │                │ • Volume: named volume     │
│   - ./api → /app/api       │                │ • Health check: enabled    │
│   - ./config → /app/config │                │ • Auto-restart: enabled    │
│ • Debug port: 5678         │                │ • Security: non-root user  │
│ • Health check: disabled   │                │ • CORS: restricted origins │
│ • Logging: DEBUG           │                │ • Logging: INFO            │
└────────────────────────────┘                └────────────────────────────┘

┌────────────────────────────┐                ┌────────────────────────────┐
│ Retraining Service         │                │ Retraining Service         │
│ • Disabled by default      │                │ • Cron enabled (Sun 2 AM)  │
│ • Manual trigger only      │                │ • Auto-restart: enabled    │
│ • Profile: manual          │                │ • Logs to volume           │
└────────────────────────────┘                └────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────┐
│                      S3 Integration (Optional)                        │
└───────────────────────────────────────────────────────────────────────┘

LOCAL (Development)                          PRODUCTION (with S3)
────────────────────────────────────         ─────────────────────────────

┌────────────────────┐                      ┌─────────────────────────┐
│  Training Service  │                      │   Training Service      │
│        ↓           │                      │          ↓              │
│  models/v1.0.0/    │                      │   models/v1.0.0/        │
│  (host volume)     │                      │          ↓              │
└────────────────────┘                      │   upload_to_s3()        │
         ↓                                  └─────────────────────────┘
┌────────────────────┐                                 ↓
│   API Service      │                      ┌─────────────────────────┐
│   (reads local)    │                      │  S3 Bucket:             │
└────────────────────┘                      │  your-model-artifacts   │
                                            │   └─ models/            │
                                            │      ├─ v1.0.0/         │
                                            │      │  ├─ cosine*.pkl  │
                                            │      │  ├─ movies*.pkl  │
                                            │      │  └─ metadata.json│
                                            │      └─ v1.1.0/         │
                                            └─────────────────────────┘
                                                       ↓
                                            ┌─────────────────────────┐
                                            │    API Service          │
                                            │    ↓                    │
                                            │  download_from_s3()     │
                                            │  (at startup)           │
                                            └─────────────────────────┘

Environment Variables:
• S3_BUCKET_NAME=your-model-artifacts-bucket
• AWS_ACCESS_KEY_ID=***
• AWS_SECRET_ACCESS_KEY=***
• RECSYS_MODEL__VERSION=v1.0.0  (switchable!)


┌───────────────────────────────────────────────────────────────────────┐
│                         Request Flow                                  │
└───────────────────────────────────────────────────────────────────────┘

Client Request
     ↓
┌─────────────────────────────────────────┐
│  http://localhost:8000/recommend        │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  CORS Middleware                        │
│  • Check origin                         │
│  • Add headers                          │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  RequestLoggingMiddleware               │
│  • Generate correlation ID (UUID)       │
│  • Log request start                    │
│  • Start timer                          │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  FastAPI Router                         │
│  • Validate request (Pydantic)          │
│  • Route to endpoint handler            │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  ContentBasedRecommender                │
│  • Lazy load models (first call)        │
│  • Check LRU cache (128 items)          │
│  • Compute similarity                   │
│  • Filter & rank results                │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  Response Generation                    │
│  • Format as RecommendResponse          │
│  • Validate with Pydantic               │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  RequestLoggingMiddleware               │
│  • Calculate duration                   │
│  • Log response                         │
│  • Record metrics                       │
│  • Add X-Correlation-ID header          │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  Response to Client                     │
│  {                                      │
│    "recommendations": [...],            │
│    "count": 5                           │
│  }                                      │
│  Headers:                               │
│    X-Correlation-ID: <uuid>             │
└─────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────┐
│                     Helper Scripts Workflow                           │
└───────────────────────────────────────────────────────────────────────┘

./docker/build.sh
├─ Build builder stage
├─ Build training stage
├─ Build serving stage
└─ Build retraining stage
   └─ Show image sizes

./docker/start-dev.sh
├─ Check if models exist
│  ├─ No → Run training
│  └─ Yes → Skip
├─ Start API with dev overrides
├─ Wait for health check
└─ Show available endpoints

./docker/train.sh [dev|prod]
├─ Select mode
├─ Run training container
└─ Remind to restart API

./docker/stop.sh [--clean]
├─ Stop all services
└─ Optional: clean volumes & images


┌───────────────────────────────────────────────────────────────────────┐
│                    Monitoring & Observability                         │
└───────────────────────────────────────────────────────────────────────┘

Metrics Endpoint: /metrics
┌─────────────────────────────────────────┐
│  {                                      │
│    "uptime_seconds": 3600,              │
│    "total_requests": 1523,              │
│    "successful_requests": 1501,         │
│    "failed_requests": 22,               │
│    "success_rate": 98.56,               │
│    "avg_latency_ms": 45.2,              │
│    "errors_by_type": {                  │
│      "ValueError": 15,                  │
│      "KeyError": 7                      │
│    },                                   │
│    "requests_by_endpoint": {            │
│      "POST /recommend": 850,            │
│      "GET /movies/1/similar": 421,      │
│      "GET /health": 252                 │
│    },                                   │
│    "status_codes": {                    │
│      "200": 1501,                       │
│      "404": 15,                         │
│      "422": 7                           │
│    }                                    │
│  }                                      │
└─────────────────────────────────────────┘

Logs (Structured JSON):
{
  "timestamp": "2026-01-31T12:34:56Z",
  "level": "INFO",
  "logger": "middleware",
  "message": "Request completed",
  "correlation_id": "a1b2c3d4-...",
  "method": "POST",
  "path": "/recommend",
  "status_code": 200,
  "duration_ms": 42.5
}

Health Check: /health
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v1.0.0",
  "model_loaded_at": "2026-01-31T10:30:00Z",
  "cache_size": 87,
  "cache_maxsize": 128
}
```
