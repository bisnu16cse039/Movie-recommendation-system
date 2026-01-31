# Docker Quick Reference

Quick commands for Movie Recommendation System Docker deployment.

## 🚀 Common Commands

### Build & Start

```bash
# Build all images
./docker/build.sh

# Start production
docker-compose up -d

# Start development with live reload
./docker/start-dev.sh

# Stop services
./docker/stop.sh

# Stop and clean everything
./docker/stop.sh --clean
```

### Training

```bash
# Manual retraining (dev)
./docker/train.sh dev

# Manual retraining (prod)
./docker/train.sh prod

# Check retraining logs
docker-compose logs retraining
```

### Monitoring

```bash
# View logs
docker-compose logs -f api

# Check health
curl http://localhost:8000/health | jq

# View metrics
curl http://localhost:8000/metrics | jq

# Container stats
docker stats recsys-api
```

### Development

```bash
# Restart API (after config changes)
docker-compose restart api

# Shell into container
docker-compose exec api bash

# View files in container
docker-compose exec api ls -lh /app/models/v1.0.0/

# Run Python in container
docker-compose exec api python -c "from src.models.recommender import ContentBasedRecommender; print('OK')"
```

## 🔍 Debugging

```bash
# View all service status
docker-compose ps

# Detailed service info
docker-compose config

# Check volumes
docker volume ls | grep recsys

# Inspect volume
docker volume inspect recsys-models

# Check network
docker network inspect recsys-network

# View container details
docker inspect recsys-api
```

## 🧪 Testing API

```bash
# Health check
curl http://localhost:8000/health

# Search movies
curl http://localhost:8000/movies/search?query=toy

# Get similar movies
curl http://localhost:8000/movies/1/similar?n=5

# Get recommendations
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_ratings": {"1": 5.0, "50": 4.0}, "n": 5}'

# Clear cache
curl -X POST http://localhost:8000/cache/clear

# View metrics
curl http://localhost:8000/metrics

# API docs (browser)
open http://localhost:8000/docs
```

## 📦 Image Management

```bash
# List images
docker images | grep movie-recsys

# Remove unused images
docker image prune -a

# Tag image for registry
docker tag movie-recsys-api:latest your-registry/movie-recsys-api:v1.0.0

# Push to registry
docker push your-registry/movie-recsys-api:v1.0.0

# Pull from registry
docker pull your-registry/movie-recsys-api:v1.0.0
```

## 🔄 Updates & Rollback

```bash
# Update to new version
git pull
./docker/build.sh
docker-compose down
docker-compose up -d

# Rollback to previous image
docker-compose down
docker tag movie-recsys-api:latest movie-recsys-api:backup
# ... restore previous image ...
docker-compose up -d

# Switch model version
export RECSYS_MODEL__VERSION=v1.1.0
docker-compose restart api
```

## 🧹 Cleanup

```bash
# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Remove all project containers
docker ps -a | grep recsys | awk '{print $1}' | xargs docker rm

# Remove all project images
docker images | grep movie-recsys | awk '{print $3}' | xargs docker rmi

# Full cleanup (nuclear option)
docker system prune -a --volumes
```

## ☁️ S3 Operations

```bash
# Upload models to S3 (Python)
python -c "
from src.utils.storage import upload_models_to_s3
from pathlib import Path
upload_models_to_s3('v1.0.0', Path('models/v1.0.0'))
"

# Download models from S3 (Python)
python -c "
from src.utils.storage import download_models_from_s3
from pathlib import Path
download_models_from_s3('v1.0.0', Path('models/v1.0.0'))
"

# List versions in S3
aws s3 ls s3://your-bucket/models/

# Sync local to S3
aws s3 sync models/v1.0.0/ s3://your-bucket/models/v1.0.0/

# Sync S3 to local
aws s3 sync s3://your-bucket/models/v1.0.0/ models/v1.0.0/
```

## 🐛 Troubleshooting

```bash
# Can't connect to Docker daemon
sudo systemctl start docker  # Linux
# or restart Docker Desktop

# Port already in use
lsof -ti:8000 | xargs kill -9

# Permission denied on volumes
sudo chown -R $USER:$USER models/ logs/

# Out of disk space
docker system df
docker system prune -a --volumes

# Container keeps restarting
docker-compose logs api --tail=50
docker-compose exec api bash  # Debug inside
```

## 🔐 Production Checklist

- [ ] Set `RECSYS_ENVIRONMENT=production`
- [ ] Configure CORS origins (not `["*"]`)
- [ ] Set proper `API__WORKERS` count
- [ ] Enable health checks
- [ ] Set up S3 for model artifacts
- [ ] Configure secrets management
- [ ] Enable HTTPS (nginx/traefik)
- [ ] Set up monitoring (Prometheus)
- [ ] Configure log aggregation
- [ ] Set up CI/CD pipeline
- [ ] Test disaster recovery

---

**See [docker/README.md](README.md) for detailed documentation**
