# Movie Recommendation API

A production-ready FastAPI application for content-based movie recommendations using the MovieLens 100k dataset.

## Features

✨ **Content-Based Recommendations**
- Personalized recommendations based on user rating history
- Item-to-item similarity using cosine/Jaccard similarity
- Genre and year-based feature engineering

🚀 **Production Ready**
- Async FastAPI endpoints
- Request/response validation with Pydantic
- LRU caching for performance
- Structured logging
- OpenAPI/Swagger documentation
- Health check endpoint
- Error handling

📊 **API Endpoints**

### Recommendations
- `POST /recommend` - Get personalized recommendations
- `GET /movies/{id}/similar` - Get similar movies

### Movie Information
- `GET /movies/{id}` - Get movie details
- `GET /movies/search` - Search movies by title

### System
- `GET /health` - Health check
- `POST /cache/clear` - Clear LRU cache

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Train the Model (if not already done)
```bash
python train_model.py
```

### 3. Start the API Server
```bash
python start_api.py
```

Or use uvicorn directly:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test the API
```bash
python test_api.py
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Example Usage

### Get Personalized Recommendations

**Request:**
```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ratings": {
      "1": 5.0,
      "50": 4.5,
      "121": 4.0
    },
    "n": 5,
    "min_rating": 3.5
  }'
```

**Response:**
```json
{
  "recommendations": [
    {
      "movie_id": 181,
      "title": "Return of the Jedi (1983)",
      "year": 1983,
      "predicted_score": 0.952
    },
    {
      "movie_id": 174,
      "title": "Raiders of the Lost Ark (1981)",
      "year": 1981,
      "predicted_score": 0.948
    }
  ],
  "count": 5,
  "request": {
    "n_input_ratings": 3,
    "n_recommendations": 5,
    "min_rating": 3.5
  }
}
```

### Get Similar Movies

**Request:**
```bash
curl "http://localhost:8000/movies/1/similar?n=5"
```

**Response:**
```json
{
  "query_movie": {
    "movie_id": 1,
    "title": "Toy Story (1995)",
    "year": 1995
  },
  "similar_movies": [
    {
      "movie_id": 405,
      "title": "Mission: Impossible (1996)",
      "year": 1996,
      "similarity": 0.866
    }
  ],
  "count": 5
}
```

### Search Movies

**Request:**
```bash
curl "http://localhost:8000/movies/search?q=star+wars&limit=5"
```

### Get Movie Details

**Request:**
```bash
curl "http://localhost:8000/movies/1"
```

**Response:**
```json
{
  "movie_id": 1,
  "title": "Toy Story (1995)",
  "year": 1995,
  "genres": ["Animation", "Children's", "Comedy"],
  "imdb_url": "http://us.imdb.com/M/title-exact?Toy%20Story%20(1995)"
}
```

## Python Client Example

```python
import requests

# Initialize
BASE_URL = "http://localhost:8000"

# Get recommendations
response = requests.post(
    f"{BASE_URL}/recommend",
    json={
        "user_ratings": {1: 5.0, 50: 4.5},
        "n": 10,
        "min_rating": 3.5
    }
)
recommendations = response.json()

# Get similar movies
response = requests.get(f"{BASE_URL}/movies/1/similar?n=10")
similar = response.json()

# Search
response = requests.get(f"{BASE_URL}/movies/search?q=star+wars")
results = response.json()
```

## Configuration

Configuration is managed through `config/config.yaml` and environment variables:

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  reload: true
  workers: 4

model:
  version: "v1.0.0"
  artifacts_dir: "models"

similarity:
  default_method: "cosine"  # or "jaccard"
```

Environment variables:
- `RECSYS_API__HOST` - API host
- `RECSYS_API__PORT` - API port
- `RECSYS_MODEL__VERSION` - Model version to load

## Performance

- **Model Loading**: ~0.5s (lazy loaded on first request)
- **Recommendation Generation**: ~50ms for 10 recommendations
- **Similar Movies**: ~5ms (cached) / ~20ms (uncached)
- **Search**: ~10ms

## Error Handling

All errors return a consistent error response:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2024-01-31T10:00:00"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid input)
- `404` - Not Found (movie doesn't exist)
- `500` - Internal Server Error

## Logging

Structured logs are written to:
- Console: INFO level
- File: `logs/api_{date}.log` (if configured)

Example log:
```
2024-01-31 10:00:00,123 - api.main - INFO - Initializing recommender...
2024-01-31 10:00:00,456 - api.main - INFO - Recommender initialized successfully
```

## Testing

Run the test suite:
```bash
# Start the server first
python start_api.py

# In another terminal, run tests
python test_api.py
```

Expected output:
```
Test Results Summary
====================
Root                 ✓ PASS
Health               ✓ PASS
Search               ✓ PASS
Movie Details        ✓ PASS
Similar Movies       ✓ PASS
Recommendations      ✓ PASS
```

## Model Information

- **Dataset**: MovieLens 100k (1,682 movies, 100,000 ratings)
- **Features**: 19 binary genre features + 1 normalized year feature
- **Similarity**: Cosine similarity on content features
- **Training**: 5-fold cross-validation
- **Metrics**: Precision@K, NDCG@K

## API Limits

- Max recommendations per request: 50
- Max similar movies per request: 50
- Max search results: 50
- Rating range: 0.5 - 5.0
- Movie IDs: 1 - 1682

## Next Steps

- [ ] Add user authentication
- [ ] Implement rate limiting
- [ ] Add A/B testing support
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Create Docker container
- [ ] Deploy to cloud (AWS/GCP/Azure)

## License

This project uses the MovieLens 100k dataset, which is provided for research purposes by GroupLens Research.
