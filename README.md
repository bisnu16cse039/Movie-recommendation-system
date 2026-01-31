# Movie Recommendation System

Production-ready content-based movie recommendation system using MovieLens 100k dataset with FastAPI and Docker deployment.

## Features

- **Content-Based Filtering**: Recommendations using genre features and release year
- **Multiple Similarity Methods**: Cosine similarity and Jaccard index
- **FastAPI REST API**: High-performance async API with auto-generated docs
- **MLOps Best Practices**: Modular training pipeline, configuration management, logging
- **Docker Deployment**: Multi-stage builds, development/production configs, scheduled retraining
- **Monitoring**: Request logging with correlation IDs, metrics endpoint, health checks
- **S3 Integration**: Optional external storage for model artifacts

## Quick Start

### Local Development

```bash
# 1. Clone and setup
git clone <repo-url>
cd Movie-recommendation-system
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 2. Train model
python train_model.py

# 3. Start API
python start_api.py

# 4. Test
curl http://localhost:8000/health
open http://localhost:8000/docs
```

### Docker Deployment

```bash
# Build and start in one command
./docker/dev.sh

# Or for production
docker-compose up -d

# View API docs
open http://localhost:8000/docs
```

See [docker/README.md](docker/README.md) for detailed Docker documentation.

## Project Structure

```
Movie-recommendation-system/
├── api/                          # FastAPI application
│   ├── main.py                  # API routes and models
│   ├── middleware.py            # Request logging, correlation IDs
│   └── metrics.py               # In-memory metrics tracking
├── config/                       # Configuration management
│   ├── config.yaml              # Development config
│   ├── config.prod.yaml         # Production overrides
│   └── settings.py              # Pydantic settings
├── src/                         # Source code
│   ├── models/
│   │   └── recommender.py       # ContentBasedRecommender class
│   ├── training/
│   │   ├── train.py            # Training pipeline
│   │   ├── feature_engineering.py
│   │   └── similarity.py       # Similarity computation
│   └── utils/
│       ├── data_loader.py      # MovieLens data loader
│       ├── logger.py           # Structured logging
│       └── storage.py          # S3 integration (optional)
├── docker/                      # Docker deployment
│   ├── build.sh                # Build images
│   ├── start-dev.sh            # Start dev environment
│   ├── train.sh                # Manual retraining
│   └── stop.sh                 # Stop services
├── ml-100k/                     # MovieLens 100k dataset
├── models/                      # Model artifacts (versioned)
├── logs/                        # Application logs
├── Dockerfile                   # Multi-stage build
├── docker-compose.yml           # Production orchestration
├── docker-compose.dev.yml       # Development overrides
├── train_model.py              # Training entry point
└── start_api.py                # API entry point
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check with cache stats |
| `/recommend` | POST | Get personalized recommendations |
| `/movies/{id}/similar` | GET | Find similar movies |
| `/movies/{id}` | GET | Get movie details |
| `/movies/search` | GET | Search movies by title |
| `/cache/clear` | POST | Clear LRU cache |
| `/metrics` | GET | Application metrics |
| `/docs` | GET | Interactive API documentation |

## Configuration

Configuration uses YAML files with Pydantic validation and environment variable support:

```yaml
# config/config.yaml
data:
  raw_data_dir: ml-100k/
  
model:
  artifacts_dir: models/
  version: v1.0.0

api:
  host: 0.0.0.0
  port: 8000
  workers: 4
  
cors:
  enabled: true
  origins: ["*"]
```

Override with environment variables using `RECSYS_` prefix:
```bash
export RECSYS_ENVIRONMENT=production
export RECSYS_API__WORKERS=8
export RECSYS_CORS__ORIGINS='["https://yourdomain.com"]'
```

## Docker Deployment

The system includes complete Docker deployment with:

### Multi-Stage Dockerfile
- **Builder stage**: System dependencies and Python packages
- **Training stage**: Generate model artifacts
- **Serving stage**: Lightweight API container
- **Retraining stage**: Scheduled model updates (weekly via cron)

### Development Mode
```bash
./docker/start-dev.sh
```
- Live code reload
- Volume mounts for instant updates
- Debug support (port 5678)
- Verbose logging

### Production Mode
```bash
docker-compose up -d
```
- Pre-trained models baked in
- Multi-worker API (4 workers)
- Health checks and auto-restart
- Scheduled retraining (Sunday 2 AM)
- Non-root user for security

### Manual Retraining
```bash
# Trigger retraining
./docker/train.sh prod

# Restart API to load new models
docker-compose restart api
```

### S3 Integration
```bash
# Set environment variables
export S3_BUCKET_NAME=your-bucket
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# Upload models to S3
python -c "
from src.utils.storage import upload_models_to_s3
from pathlib import Path
upload_models_to_s3('v1.0.0', Path('models/v1.0.0'))
"
```

See [docker/README.md](docker/README.md) for complete documentation and [docker/QUICKREF.md](docker/QUICKREF.md) for command reference.

## Monitoring

### Metrics Endpoint
```bash
curl http://localhost:8000/metrics
```

Returns:
- Request counts (total, successful, failed)
- Average latency
- Error breakdown by type
- Requests per endpoint
- Uptime

### Logging
- Structured JSON logging
- Correlation IDs for request tracking
- Request/response timing
- Error tracking with context

### Health Checks
```bash
curl http://localhost:8000/health
```

Returns:
- API status
- Model loaded status
- Cache statistics
- Loaded at timestamp

## Dataset

MovieLens 100k dataset:
- 1,682 movies
- 943 users  
- 100,000 ratings
- 19 genre categories
- Released 1995-1998

Download from: https://grouplens.org/datasets/movielens/100k/

## Development

### Training Pipeline
```bash
python train_model.py
```

Generates:
- `cosine_similarity_matrix.pkl` - Primary similarity matrix
- `jaccard_similarity_matrix.pkl` - Genre-based similarity
- `movies_features.pkl` - Feature matrix with genres + year
- `metadata.json` - Training metadata
- `config_snapshot.json` - Configuration snapshot

### API Development
```bash
# With auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or use the start script
python start_api.py
```

## License

[Your License]

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Contact

[Your Contact Info]
