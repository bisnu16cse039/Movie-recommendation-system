"""Configuration management using Pydantic"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml


class DataConfig(BaseModel):
    """Data-related configuration"""
    raw_data_dir: str = "ml-100k/"
    movies_file: str = "u.item"
    ratings_file: str = "u.data"
    users_file: str = "u.user"


class ModelConfig(BaseModel):
    """Model-related configuration"""
    artifacts_dir: str = "models/"
    version: str = "v1.0.0"


class FeaturesConfig(BaseModel):
    """Feature engineering configuration"""
    year_weight: float = 0.1
    genre_columns: List[str] = Field(default_factory=lambda: [
        "unknown", "Action", "Adventure", "Animation", "Children", "Comedy",
        "Crime", "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror",
        "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western"
    ])


class SimilarityConfig(BaseModel):
    """Similarity computation configuration"""
    methods: List[str] = Field(default_factory=lambda: ["cosine", "jaccard"])
    default_method: str = "cosine"


class TrainingConfig(BaseModel):
    """Training configuration"""
    min_rating_threshold: float = 3.5
    random_seed: int = 42


class EvaluationConfig(BaseModel):
    """Evaluation configuration"""
    k_values: List[int] = Field(default_factory=lambda: [5, 10])
    min_relevant_rating: float = 4.0
    n_folds: int = 5


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"
    log_dir: str = "logs/"


class APIConfig(BaseModel):
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 4
    max_recommendations: int = 50
    default_recommendations: int = 10


class Settings(BaseSettings):
    """Main settings class that loads configuration from YAML and environment"""
    
    data: DataConfig = Field(default_factory=DataConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    similarity: SimilarityConfig = Field(default_factory=SimilarityConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    
    # Environment-specific overrides
    environment: str = Field(default="development", env="ENVIRONMENT")
    project_root: Optional[Path] = None
    
    class Config:
        env_prefix = "RECSYS_"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set project root if not provided
        if self.project_root is None:
            self.project_root = Path(__file__).parent.parent
    
    @classmethod
    def from_yaml(cls, config_path: str = "config/config.yaml") -> "Settings":
        """Load settings from YAML file"""
        # Get project root
        project_root = Path(__file__).parent.parent
        config_file = project_root / config_path
        
        if not config_file.exists():
            print(f"Warning: Config file {config_file} not found. Using defaults.")
            return cls()
        
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)
        
        # Create nested config objects
        settings_dict = {}
        for key, value in config_dict.items():
            if key == "data":
                settings_dict["data"] = DataConfig(**value)
            elif key == "model":
                settings_dict["model"] = ModelConfig(**value)
            elif key == "features":
                settings_dict["features"] = FeaturesConfig(**value)
            elif key == "similarity":
                settings_dict["similarity"] = SimilarityConfig(**value)
            elif key == "training":
                settings_dict["training"] = TrainingConfig(**value)
            elif key == "evaluation":
                settings_dict["evaluation"] = EvaluationConfig(**value)
            elif key == "logging":
                settings_dict["logging"] = LoggingConfig(**value)
            elif key == "api":
                settings_dict["api"] = APIConfig(**value)
        
        return cls(**settings_dict, project_root=project_root)
    
    def get_data_path(self, filename: str) -> Path:
        """Get absolute path for data file"""
        return self.project_root / self.data.raw_data_dir / filename
    
    def get_model_path(self, filename: str) -> Path:
        """Get absolute path for model artifact"""
        model_dir = self.project_root / self.model.artifacts_dir / self.model.version
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir / filename
    
    def get_log_path(self, filename: str) -> Path:
        """Get absolute path for log file"""
        log_dir = self.project_root / self.logging.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / filename


# Global settings instance
settings = Settings.from_yaml()


if __name__ == "__main__":
    # Test configuration loading
    print("Configuration loaded successfully!")
    print(f"Environment: {settings.environment}")
    print(f"Project root: {settings.project_root}")
    print(f"Year weight: {settings.features.year_weight}")
    print(f"Default similarity method: {settings.similarity.default_method}")
    print(f"Model version: {settings.model.version}")
