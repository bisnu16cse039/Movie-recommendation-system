"""Main training pipeline for content-based recommendation system"""

import sys
from pathlib import Path
import pickle
import json
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from src.utils.logger import setup_logger, log_execution_time
from src.utils.data_loader import load_movies_data
from src.training.feature_engineering import FeatureEngineer
from src.training.similarity import SimilarityComputer


class TrainingPipeline:
    """Main training pipeline for content-based recommendation system"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize training pipeline.
        
        Parameters:
        -----------
        config_path : str
            Path to configuration YAML file
        """
        # Load configuration
        self.settings = Settings.from_yaml(config_path)
        
        # Setup logger
        self.logger = setup_logger(
            name="training_pipeline",
            log_level=self.settings.logging.level,
            log_format=self.settings.logging.format,
            log_dir=self.settings.get_log_path(""),
            log_to_console=True,
            log_to_file=True
        )
        
        self.logger.info("="*80)
        self.logger.info("CONTENT-BASED RECOMMENDATION SYSTEM - TRAINING PIPELINE")
        self.logger.info("="*80)
        self.logger.info(f"Model version: {self.settings.model.version}")
        self.logger.info(f"Environment: {self.settings.environment}")
        self.logger.info(f"Project root: {self.settings.project_root}")
        
        # Initialize components
        self.feature_engineer = FeatureEngineer(
            year_weight=self.settings.features.year_weight,
            genre_columns=self.settings.features.genre_columns
        )
        self.similarity_computer = SimilarityComputer()
        
        # Storage for artifacts
        self.movies = None
        self.movies_features = None
        self.feature_matrix = None
        self.similarity_matrices = {}
    
    def load_data(self):
        """Load movie data from files"""
        import time
        start_time = time.time()
        self.logger.info("\nStep 1: Loading data...")
        self.logger.info("-"*80)
        
        # Get data directory path
        data_dir = self.settings.project_root / self.settings.data.raw_data_dir
        
        self.movies = load_movies_data(
            data_dir=str(data_dir),
            genre_columns=self.settings.features.genre_columns
        )
        
        self.logger.info(f"✓ Loaded {len(self.movies)} movies")
        self.logger.info(f"  Year range: {self.movies['year'].min():.0f} - {self.movies['year'].max():.0f}")
        
        # Check for movies without genres
        no_genres = (self.movies[self.settings.features.genre_columns].sum(axis=1) == 0).sum()
        if no_genres > 0:
            self.logger.warning(f"  {no_genres} movies have no genres assigned")
        
        elapsed = time.time() - start_time
        self.logger.info(f"✓ Data loading completed in {elapsed:.2f}s")
    
    def engineer_features(self):
        """Engineer features from raw movie data"""
        import time
        start_time = time.time()
        
        self.logger.info("\nStep 2: Engineering features...")
        self.logger.info("-"*80)
        
        self.movies_features, self.feature_matrix = self.feature_engineer.fit_transform(
            self.movies
        )
        
        self.logger.info(f"✓ Feature matrix created: {self.feature_matrix.shape}")
        self.logger.info(f"  Total features: {self.feature_matrix.shape[1]}")
        self.logger.info(f"    - Genre features: {len(self.settings.features.genre_columns)}")
        self.logger.info(f"    - Year feature: 1 (weighted by {self.settings.features.year_weight})")
        
        elapsed = time.time() - start_time
        self.logger.info(f"✓ Feature engineering completed in {elapsed:.2f}s")
    
    def compute_similarities(self):
        """Compute similarity matrices"""
        import time
        start_time = time.time()
        
        self.logger.info("\nStep 3: Computing similarity matrices...")
        self.logger.info("-"*80)
        
        self.similarity_matrices = self.similarity_computer.compute_all_similarities(
            feature_matrix=self.feature_matrix,
            genre_columns=self.settings.features.genre_columns,
            movies_features=self.movies_features,
            methods=self.settings.similarity.methods
        )
        
        self.logger.info(f"✓ Computed {len(self.similarity_matrices)} similarity matrices")
        for method in self.similarity_matrices:
            self.logger.info(f"  - {method}: {self.similarity_matrices[method].shape}")
        
        elapsed = time.time() - start_time
        self.logger.info(f"✓ Similarity computation completed in {elapsed:.2f}s")
    
    def save_artifacts(self):
        """Save all trained artifacts"""
        import time
        start_time = time.time()
        
        self.logger.info("\nStep 4: Saving artifacts...")
        self.logger.info("-"*80)
        
        # Create versioned model directory
        model_dir = self.settings.project_root / self.settings.model.artifacts_dir / self.settings.model.version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Saving artifacts to: {model_dir}")
        
        # 1. Save similarity matrices
        for method, matrix in self.similarity_matrices.items():
            matrix_path = model_dir / f"{method}_similarity_matrix.pkl"
            with open(matrix_path, 'wb') as f:
                pickle.dump(matrix, f, protocol=pickle.HIGHEST_PROTOCOL)
            self.logger.info(f"  ✓ Saved {method} similarity matrix: {matrix_path.name}")
        
        # 2. Save movies_features dataframe
        movies_path = model_dir / "movies_features.pkl"
        self.movies_features.to_pickle(movies_path)
        self.logger.info(f"  ✓ Saved movies features: {movies_path.name}")
        
        # Also save as CSV for human readability
        movies_csv_path = model_dir / "movies_features.csv"
        self.movies_features.to_csv(movies_csv_path, index=False)
        self.logger.info(f"  ✓ Saved movies CSV: {movies_csv_path.name}")
        
        # 3. Save feature engineer (scaler)
        scaler_path = model_dir / "feature_scaler.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.feature_engineer, f)
        self.logger.info(f"  ✓ Saved feature scaler: {scaler_path.name}")
        
        # 4. Save configuration and metadata
        metadata = {
            'model_version': self.settings.model.version,
            'trained_at': datetime.now().isoformat(),
            'n_movies': len(self.movies),
            'n_features': self.feature_matrix.shape[1],
            'year_weight': self.settings.features.year_weight,
            'genre_columns': self.settings.features.genre_columns,
            'similarity_methods': list(self.similarity_matrices.keys()),
            'default_similarity_method': self.settings.similarity.default_method,
            'feature_matrix_shape': list(self.feature_matrix.shape),
            'year_range': {
                'min': float(self.movies['year'].min()),
                'max': float(self.movies['year'].max())
            }
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        self.logger.info(f"  ✓ Saved metadata: {metadata_path.name}")
        
        # 5. Save configuration snapshot
        config_snapshot = {
            'data': self.settings.data.model_dump(),
            'model': self.settings.model.model_dump(),
            'features': self.settings.features.model_dump(),
            'similarity': self.settings.similarity.model_dump(),
            'training': self.settings.training.model_dump()
        }
        
        config_path = model_dir / "config_snapshot.json"
        with open(config_path, 'w') as f:
            json.dump(config_snapshot, f, indent=2)
        self.logger.info(f"  ✓ Saved config snapshot: {config_path.name}")
        
        elapsed = time.time() - start_time
        self.logger.info(f"\n✓ All artifacts saved to: {model_dir}")
        self.logger.info(f"✓ Artifact saving completed in {elapsed:.2f}s")
    
    def run(self):
        """Run the complete training pipeline"""
        try:
            self.logger.info("\n" + "="*80)
            self.logger.info("STARTING TRAINING PIPELINE")
            self.logger.info("="*80)
            
            # Execute pipeline steps
            self.load_data()
            self.engineer_features()
            self.compute_similarities()
            self.save_artifacts()
            
            self.logger.info("\n" + "="*80)
            self.logger.info("✅ TRAINING PIPELINE COMPLETED SUCCESSFULLY")
            self.logger.info("="*80)
            self.logger.info(f"Model version: {self.settings.model.version}")
            self.logger.info(f"Artifacts saved to: {self.settings.model.artifacts_dir}/{self.settings.model.version}")
            
        except Exception as e:
            self.logger.error(f"\n❌ TRAINING PIPELINE FAILED: {str(e)}", exc_info=True)
            raise


def main():
    """Main entry point for training pipeline"""
    parser = argparse.ArgumentParser(
        description="Train content-based movie recommendation system"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--version',
        type=str,
        help='Model version (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Initialize and run pipeline
    pipeline = TrainingPipeline(config_path=args.config)
    
    # Override version if provided
    if args.version:
        pipeline.settings.model.version = args.version
        pipeline.logger.info(f"Using model version from argument: {args.version}")
    
    pipeline.run()


if __name__ == "__main__":
    main()
