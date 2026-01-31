# Docker Deployment Guide

Complete Docker deployment for Movie Recommendation System with multi-stage builds, development/production configurations, and S3 integration.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Development Mode](#development-mode)
- [Production Deployment](#production-deployment)
- [Manual Retraining](#manual-retraining)
- [S3 Integration](#s3-integration)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture Overview

### Multi-Stage Dockerfile

The system uses a single Dockerfile with four build stages:

```
┌──────────────────────────────────────────────────────────┐
│ Stage 1: BUILDER                                         │
│ - Base Python 3.10-slim                                  │
│ - Install system dependencies (gcc, g++, make)           │
│ - Install Python packages from requirements.txt          │
│ - Size: ~400MB                                           │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│ Stage 2: TRAINING                                        │
│ - Copy application code and ml-100k/ dataset             │
│ - Run train_model.py to generate artifacts              │
│ - Output: models/v1.0.0/ with .pkl files (~50MB)        │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│ Stage 3: SERVING (API)                                   │
│ - Lightweight Python 3.10-slim base                      │
│ - Copy pre-trained models from training stage            │
│ - Copy API code (api/, src/, config/)                    │
│ - Non-root user (recsys:1000)                            │
│ - Expose port 8000, health check enabled                 │
│ - Size: ~500MB                                           │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│ Stage 4: RETRAINING                                      │
│ - Based on builder stage                                 │
│ - Install cron for scheduled retraining                  │
│ - Runs weekly on Sunday at 2 AM                          │
│ - Supports manual trigger                                │
└──────────────────────────────────────────────────────────┘
```

### Services

| Service | Purpose | Restart Policy | Volumes |
|---------|---------|----------------|---------|
| **training** | One-time model training | no | ml-100k/ (ro), models/, logs/ |
| **api** | FastAPI REST API | unless-stopped | models/ (ro), ml-100k/ (ro), logs/ |
| **retraining** | Scheduled/manual retraining | unless-stopped | ml-100k/ (ro), models/ (rw), logs/ |

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- 2GB RAM minimum
- 5GB disk space

### 1. Build Images

```bash
# Build all stages (takes 3-5 minutes)
./docker/build.sh

# Build without cache (if you change requirements.txt)
./docker/build.sh --no-cache
```

### 2. Start Production Services

```bash
# Start training + API in production mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 3. Verify API

```bash
# Health check
curl http://localhost:8000/health

# Get recommendations
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_ratings": {"1": 5.0, "50": 4.0}, "n": 5}'

# View metrics
curl http://localhost:8000/metrics

# API documentation
open http://localhost:8000/docs
```

---

## 💻 Development Mode

Development mode enables:
- **Live code reload** - Changes to Python files trigger auto-reload
- **Volume mounts** - Edit code on host, reflected immediately in container
- **Debug support** - Debugpy port exposed on 5678
- **Single worker** - Easier debugging with `RECSYS_API__WORKERS=1`
- **Verbose logging** - `DEBUG` level logs

### Start Development Environment

```bash
# One command to rule them all
./docker/start-dev.sh
```

This script:
1. Checks if models exist locally
2. Runs training if needed
3. Starts API with live reload
4. Shows available endpoints and commands

### Manual Steps

```bash
# Start services with dev overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs in real-time
docker-compose logs -f api

# Restart API after config changes
docker-compose restart api

# Stop services
./docker/stop.sh
```

### Development Workflow

```bash
# 1. Edit code in your IDE
vim src/models/recommender.py

# 2. API auto-reloads automatically
# Check logs: docker-compose logs -f api

# 3. Test changes
curl http://localhost:8000/health

# 4. Commit when ready
git add .
git commit -m "Update recommender logic"
```

### Remote Debugging

```python
# Add to your code
import debugpy
debugpy.listen(("0.0.0.0", 5678))
debugpy.wait_for_client()  # Optional: pause until debugger attaches
```

Then connect from VS Code:
```json
{
  "name": "Docker: Attach to API",
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  },
  "pathMappings": [
    {"localRoot": "${workspaceFolder}", "remoteRoot": "/app"}
  ]
}
```

---

## 🚢 Production Deployment

### Configuration

Production mode uses:
- `config/config.prod.yaml` overrides
- `RECSYS_ENVIRONMENT=production` env var
- 4 Uvicorn workers (configurable)
- Auto-restart on failure
- Health checks every 30s
- Restricted CORS (configure origins)
- Non-root user for security

### Environment Variables

Create a `.env` file (ignored by git):

```bash
# Application
RECSYS_ENVIRONMENT=production
RECSYS_MODEL__VERSION=v1.0.0

# API Configuration
RECSYS_API__HOST=0.0.0.0
RECSYS_API__PORT=8000
RECSYS_API__WORKERS=4
RECSYS_API__RELOAD=false

# CORS (restrict in production!)
RECSYS_CORS__ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]

# Logging
RECSYS_LOGGING__LEVEL=INFO

# S3 Storage (optional - see S3 Integration section)
S3_BUCKET_NAME=your-model-artifacts-bucket
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
```

### Deployment Commands

```bash
# Load environment variables
export $(cat .env | xargs)

# Start services
docker-compose up -d

# Check health
docker-compose ps
docker-compose logs api | grep "Application startup complete"

# Scale API workers (if not using Uvicorn workers)
docker-compose up -d --scale api=3

# Update to new version
docker-compose down
docker-compose pull  # If using registry
docker-compose up -d
```

### Monitoring

```bash
# View metrics
curl http://localhost:8000/metrics | jq

# Check logs
docker-compose logs --tail=100 -f api

# Container stats
docker stats recsys-api

# Health check
watch -n 5 'curl -s http://localhost:8000/health | jq'
```

---

## 🔄 Manual Retraining

### Trigger Retraining

```bash
# Development mode
./docker/train.sh dev

# Production mode
./docker/train.sh prod

# Or use docker-compose directly
docker-compose run --rm retraining python train_model.py
```

### Restart API to Load New Models

```bash
# Restart API service
docker-compose restart api

# Verify new models loaded
curl http://localhost:8000/health | jq '.model_loaded_at'
```

### Scheduled Retraining

The retraining service runs automatically via cron:
- **Schedule**: Weekly on Sunday at 2 AM
- **Logs**: `logs/retraining.log`
- **Restart API**: Manual (or add webhook)

Check retraining logs:
```bash
docker-compose logs retraining

# Or view log file directly
docker-compose exec retraining cat /app/logs/retraining.log
```

---

## ☁️ S3 Integration

For production deployments, store model artifacts in S3 instead of baking them into the Docker image.

### Setup

1. **Install boto3** (add to requirements.txt):
```bash
echo "boto3>=1.34.0" >> requirements.txt
```

2. **Create S3 bucket**:
```bash
aws s3 mb s3://your-model-artifacts-bucket
```

3. **Set environment variables**:
```bash
export S3_BUCKET_NAME=your-model-artifacts-bucket
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
```

### Upload Models to S3

After training locally:

```python
from src.utils.storage import upload_models_to_s3
from pathlib import Path

# Upload entire model version
upload_models_to_s3(
    version="v1.0.0",
    local_dir=Path("models/v1.0.0"),
    bucket_name="your-model-artifacts-bucket"
)
```

Or use the CLI:
```bash
python -c "
from src.utils.storage import upload_models_to_s3
from pathlib import Path
upload_models_to_s3('v1.0.0', Path('models/v1.0.0'))
"
```

### Download Models at API Startup

Modify `src/models/recommender.py` to download from S3 if models don't exist:

```python
from src.utils.storage import download_models_from_s3

class ContentBasedRecommender:
    def __init__(self, model_dir: Path, ...):
        self.model_dir = model_dir
        
        # Download from S3 if models don't exist locally
        if not (self.model_dir / "cosine_similarity_matrix.pkl").exists():
            logger.info("Models not found locally, downloading from S3...")
            download_models_from_s3(
                version="v1.0.0",
                local_dir=self.model_dir,
                bucket_name=os.getenv("S3_BUCKET_NAME")
            )
```

### Benefits of S3 Storage

- ✅ **Smaller Docker images** - No 50MB model files baked in
- ✅ **Version control** - Store multiple model versions
- ✅ **Separate training/serving** - Train anywhere, serve anywhere
- ✅ **Easy rollback** - Switch versions by changing env var
- ✅ **Cost effective** - S3 cheaper than container registry for large files

---

## 🔧 Troubleshooting

### API Won't Start

**Check logs:**
```bash
docker-compose logs api
```

**Common issues:**
- Models not found → Run training first: `docker-compose run --rm training`
- Port 8000 in use → Change port in docker-compose.yml
- Permission errors → Check volume ownership: `ls -la models/`

### Training Fails

```bash
# View training logs
docker-compose logs training

# Run interactively for debugging
docker-compose run --rm training bash
# Inside container:
python train_model.py
```

### Models Not Loading

```bash
# Verify models exist
docker-compose exec api ls -lh /app/models/v1.0.0/

# Check permissions
docker-compose exec api stat /app/models/v1.0.0/cosine_similarity_matrix.pkl

# Verify model path in config
docker-compose exec api cat /app/config/config.yaml | grep model
```

### Slow Performance

- Increase API workers: `RECSYS_API__WORKERS=8`
- Scale API containers: `docker-compose up -d --scale api=3`
- Add caching layer (Redis) in front of API
- Use load balancer (nginx) for multiple API instances

### Memory Issues

```bash
# Check container memory
docker stats

# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory: 4GB

# Reduce API workers
export RECSYS_API__WORKERS=2
```

### Clean Slate

```bash
# Stop all services and clean up
./docker/stop.sh --clean

# Remove all data (WARNING: deletes models!)
docker volume prune -f

# Rebuild everything
./docker/build.sh --no-cache
docker-compose up -d
```

---

## 📊 Image Sizes

Expected sizes after build:

| Image | Size | Purpose |
|-------|------|---------|
| movie-recsys-builder | ~400MB | Base with all dependencies |
| movie-recsys-training | ~450MB | Builder + training code |
| movie-recsys-api | ~500MB | Slim + models + API code |
| movie-recsys-retraining | ~420MB | Builder + cron |

Optimize by:
- Using multi-stage builds (already implemented)
- Removing dev dependencies in production stage
- Storing models in S3 (saves 50MB per image)
- Using slim/alpine base images

---

## 🎯 Best Practices

### Security
- ✅ Non-root user (recsys:1000)
- ✅ No secrets in Dockerfile
- ✅ Restrict CORS origins in production
- ⚠️ Use secrets management for AWS credentials
- ⚠️ Enable HTTPS in production (use nginx/traefik)

### Performance
- ✅ Multi-worker API (4 workers by default)
- ✅ Health checks for auto-restart
- ✅ Shared model volume (no duplication)
- ⚠️ Add Redis for distributed caching
- ⚠️ Use load balancer for horizontal scaling

### Reliability
- ✅ Auto-restart on failure
- ✅ Health checks every 30s
- ✅ Structured logging with correlation IDs
- ✅ Metrics endpoint for monitoring
- ⚠️ Add alerting (Prometheus + Grafana)
- ⚠️ Implement graceful shutdown

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [AWS S3 with boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)

---

## 🤝 Contributing

Found an issue or have an improvement?
1. Edit the relevant Dockerfile stage or compose file
2. Test thoroughly in dev mode
3. Update this documentation
4. Submit a PR

---

**Last Updated**: January 31, 2026
