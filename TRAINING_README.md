# Movie Recommendation System - MLOps Production Pipeline

Content-based movie recommendation system with FastAPI deployment following MLOps best practices.

## Project Structure

```
Movie-recommendation-system/
├── config/                      # Configuration files
│   ├── config.yaml             # Main configuration
│   └── settings.py             # Pydantic settings management
├── src/                        # Source code
│   ├── training/               # Training pipeline
│   │   ├── train.py           # Main training script
│   │   ├── feature_engineering.py
│   │   └── similarity.py
│   ├── models/                 # Inference models (Step 3)
│   │   └── recommender.py
│   └── utils/                  # Utility functions
│       ├── data_loader.py
│       └── logger.py
├── api/                        # FastAPI application (Step 4)
│   └── main.py
├── models/                     # Saved model artifacts
│   └── v1.0.0/                # Versioned artifacts
│       ├── cosine_similarity_matrix.pkl
│       ├── jaccard_similarity_matrix.pkl
│       ├── movies_features.pkl
│       ├── feature_scaler.pkl
│       └── metadata.json
├── tests/                      # Unit and integration tests
├── logs/                       # Application logs
├── ml-100k/                    # MovieLens dataset
├── requirements.txt            # Python dependencies
├── train_model.py              # Training script entry point
└── README.md                   # This file
```

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Data

Ensure MovieLens 100k dataset is in `ml-100k/` directory:
- `u.item` - Movie metadata
- `u.data` - Ratings data
- `u1.base` - `u5.base` - Training folds
- `u1.test` - `u5.test` - Test folds

## Training Pipeline (Steps 1-2 ✅)

### Quick Start

```bash
# Train model with default configuration
python train_model.py

# Train with specific version
python train_model.py --version v1.1.0

# Train with custom config
python train_model.py --config config/config.yaml
```

### What the Training Pipeline Does

1. **Load Data** - Reads MovieLens movies data with genres and years
2. **Engineer Features** - Creates feature matrix (19 genres + 1 normalized year)
3. **Compute Similarities** - Calculates cosine and Jaccard similarity matrices
4. **Save Artifacts** - Persists all model artifacts with versioning

### Output Artifacts

After training, the following artifacts are saved in `models/v1.0.0/`:

- `cosine_similarity_matrix.pkl` - Cosine similarity matrix (1682×1682)
- `jaccard_similarity_matrix.pkl` - Jaccard similarity matrix (genres only)
- `movies_features.pkl` - Movie metadata with engineered features
- `movies_features.csv` - Human-readable movie data
- `feature_scaler.pkl` - Fitted MinMaxScaler for year normalization
- `metadata.json` - Training metadata and statistics
- `config_snapshot.json` - Configuration used for training

### Training Logs

Logs are saved to `logs/training_pipeline_YYYYMMDD.log` in JSON format for easy parsing.

## Configuration

Edit `config/config.yaml` to customize:

```yaml
features:
  year_weight: 0.1  # Weight for year feature (0.1 = genres 10x more important)
  
similarity:
  methods:
    - cosine   # Primary method
    - jaccard  # Secondary method
  default_method: cosine

model:
  version: "v1.0.0"  # Model version for artifact storage
```

## Model Architecture

### Feature Engineering
- **Input**: Movie metadata (title, release year, 19 binary genre features)
- **Processing**: 
  - Extract year from title
  - Normalize year to [0, 0.1] range (makes genres 10x more important)
  - Create feature matrix: [genres (19) + year_normalized (1)]
- **Output**: 1682 movies × 20 features

### Similarity Computation
- **Cosine Similarity** (Primary): Angle between feature vectors
- **Jaccard Similarity** (Secondary): Genre overlap only

### Why This Approach?
- **Genre prioritization**: Year weight = 0.1 ensures genre matching dominates
- **Pre-computed similarities**: No runtime computation needed
- **Scalable**: Matrix lookup is O(1) per movie pair

## Development

### Code Quality

```bash
# Format code
black src/ config/ train_model.py

# Lint
flake8 src/ config/

# Type check
mypy src/
```

### Testing (Step 7)

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Next Steps

- [x] **Step 1**: Project structure ✅
- [x] **Step 2**: Training pipeline ✅
- [ ] **Step 3**: Inference module (`src/models/recommender.py`)
- [ ] **Step 4**: FastAPI application (`api/main.py`)
- [ ] **Step 5**: Configuration management (completed)
- [ ] **Step 6**: Logging and monitoring
- [ ] **Step 7**: Unit and integration tests
- [ ] **Step 8**: Docker deployment
- [ ] **Step 9**: CI/CD pipeline
- [ ] **Step 10**: Documentation and deployment guide

## MLOps Best Practices Implemented

✅ **Modular Code Structure**: Separation of training, inference, and API layers
✅ **Configuration Management**: YAML config with Pydantic validation
✅ **Logging**: Structured JSON logging with multiple handlers
✅ **Versioning**: Timestamped model versions with metadata
✅ **Reproducibility**: Config snapshots saved with artifacts
✅ **Data Validation**: Pydantic models for type safety
✅ **Separation of Concerns**: Clear boundaries between components

## License

MIT
