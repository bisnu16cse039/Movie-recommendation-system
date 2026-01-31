"""Feature engineering for content-based recommendation"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Feature engineering for movie content-based filtering"""
    
    def __init__(self, year_weight: float = 0.1, genre_columns: list = None):
        """
        Initialize feature engineer.
        
        Parameters:
        -----------
        year_weight : float
            Weight for year feature relative to genre features
        genre_columns : list
            List of genre column names
        """
        self.year_weight = year_weight
        self.genre_columns = genre_columns or []
        self.scaler = MinMaxScaler()
        self.is_fitted = False
        
        logger.info(f"Initialized FeatureEngineer with year_weight={year_weight}")
    
    def fit_transform(self, movies: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Fit scaler and transform movie data into feature matrix.
        
        Parameters:
        -----------
        movies : pd.DataFrame
            Movies dataframe with genre columns and year
        
        Returns:
        --------
        Tuple[pd.DataFrame, np.ndarray] : 
            - movies_features: DataFrame with all features including normalized year
            - feature_matrix: Numpy array of shape (n_movies, n_features)
        """
        logger.info("Fitting and transforming features")
        
        # Create a copy for feature engineering
        movies_features = movies.copy()
        
        # Check for missing values
        missing_years = movies_features['year'].isna().sum()
        if missing_years > 0:
            logger.warning(f"Found {missing_years} movies with missing year")
            median_year = movies_features['year'].median()
            movies_features['year'].fillna(median_year, inplace=True)
            logger.info(f"Filled missing years with median: {median_year}")
        
        # Normalize year to small range [0, year_weight]
        # This makes genres more important than year in similarity calculations
        movies_features['year_normalized'] = (
            self.scaler.fit_transform(movies_features[['year']]) * self.year_weight
        )
        
        self.is_fitted = True
        
        # Create feature matrix: genres + normalized year
        feature_columns = self.genre_columns + ['year_normalized']
        feature_matrix = movies_features[feature_columns].values
        
        logger.info(f"Feature matrix created: shape={feature_matrix.shape}")
        logger.info(f"  Genre features: {len(self.genre_columns)} (weight: 1.0 each)")
        logger.info(f"  Year feature: 1 (weight: {self.year_weight})")
        logger.info(f"  Value range: [{feature_matrix.min():.3f}, {feature_matrix.max():.3f}]")
        
        return movies_features, feature_matrix
    
    def transform(self, movies: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Transform movie data using fitted scaler (for new data).
        
        Parameters:
        -----------
        movies : pd.DataFrame
            Movies dataframe with genre columns and year
        
        Returns:
        --------
        Tuple[pd.DataFrame, np.ndarray] : 
            - movies_features: DataFrame with all features
            - feature_matrix: Numpy array
        """
        if not self.is_fitted:
            raise ValueError("FeatureEngineer must be fitted before transform")
        
        logger.info("Transforming features with fitted scaler")
        
        movies_features = movies.copy()
        
        # Handle missing years
        if movies_features['year'].isna().sum() > 0:
            median_year = movies_features['year'].median()
            movies_features['year'].fillna(median_year, inplace=True)
        
        # Transform year using fitted scaler
        movies_features['year_normalized'] = (
            self.scaler.transform(movies_features[['year']]) * self.year_weight
        )
        
        # Create feature matrix
        feature_columns = self.genre_columns + ['year_normalized']
        feature_matrix = movies_features[feature_columns].values
        
        logger.info(f"Transformed feature matrix: shape={feature_matrix.shape}")
        
        return movies_features, feature_matrix
    
    def get_feature_names(self) -> list:
        """Get list of feature column names"""
        return self.genre_columns + ['year_normalized']
