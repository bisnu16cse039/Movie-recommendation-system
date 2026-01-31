"""Data loading utilities for MovieLens dataset"""

import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def load_movies_data(
    data_dir: str,
    genre_columns: list
) -> pd.DataFrame:
    """
    Load and preprocess movies data from u.item file.
    
    Parameters:
    -----------
    data_dir : str
        Directory containing MovieLens data files
    genre_columns : list
        List of genre column names
    
    Returns:
    --------
    pd.DataFrame : Movies dataframe with genres and extracted year
    """
    logger.info(f"Loading movies data from {data_dir}")
    
    # Define all column names for u.item
    column_names = ['movie_id', 'title', 'release_date', 'video_release_date', 'IMDb_URL'] + genre_columns
    
    # Load movies data
    movies = pd.read_csv(
        Path(data_dir) / 'u.item',
        sep='|',
        names=column_names,
        encoding='latin-1'
    )
    
    # Extract year from title (format: "Movie Name (YYYY)")
    movies['year'] = movies['title'].str.extract(r'\((\d{4})\)', expand=False).astype(float)
    
    # Handle missing years - fill with median
    if movies['year'].isna().sum() > 0:
        median_year = movies['year'].median()
        movies['year'].fillna(median_year, inplace=True)
        logger.info(f"Filled {movies['year'].isna().sum()} missing years with median: {median_year}")
    
    logger.info(f"Loaded {len(movies)} movies")
    logger.info(f"  Year range: {movies['year'].min():.0f} to {movies['year'].max():.0f}")
    logger.info(f"  Movies with genres: {(movies[genre_columns].sum(axis=1) > 0).sum()}")
    
    return movies


def load_ratings_data(
    data_dir: str,
    convert_timestamp: bool = True
) -> pd.DataFrame:
    """
    Load ratings data from u.data file.
    
    Parameters:
    -----------
    data_dir : str
        Directory containing MovieLens data files
    convert_timestamp : bool
        Whether to convert timestamp to datetime
    
    Returns:
    --------
    pd.DataFrame : Ratings dataframe
    """
    logger.info(f"Loading ratings data from {data_dir}")
    
    ratings = pd.read_csv(
        Path(data_dir) / 'u.data',
        sep='\t',
        names=['user_id', 'item_id', 'rating', 'timestamp'],
        encoding='latin-1'
    )
    
    if convert_timestamp:
        ratings['datetime'] = pd.to_datetime(ratings['timestamp'], unit='s')
    
    logger.info(f"Loaded {len(ratings):,} ratings")
    logger.info(f"  Users: {ratings['user_id'].nunique()}")
    logger.info(f"  Movies: {ratings['item_id'].nunique()}")
    logger.info(f"  Rating range: {ratings['rating'].min()} to {ratings['rating'].max()}")
    
    return ratings


def load_fold_data(
    data_dir: str,
    fold_number: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load train/test split for a specific fold.
    
    Parameters:
    -----------
    data_dir : str
        Directory containing MovieLens data files
    fold_number : int
        Fold number (1-5)
    
    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame] : (train_ratings, test_ratings)
    """
    if not 1 <= fold_number <= 5:
        raise ValueError(f"Fold number must be between 1 and 5, got {fold_number}")
    
    logger.info(f"Loading fold {fold_number} data")
    
    # Load training data
    train_ratings = pd.read_csv(
        Path(data_dir) / f'u{fold_number}.base',
        sep='\t',
        names=['user_id', 'item_id', 'rating', 'timestamp'],
        encoding='latin-1'
    )
    
    # Load test data
    test_ratings = pd.read_csv(
        Path(data_dir) / f'u{fold_number}.test',
        sep='\t',
        names=['user_id', 'item_id', 'rating', 'timestamp'],
        encoding='latin-1'
    )
    
    logger.info(f"  Train: {len(train_ratings):,} ratings")
    logger.info(f"  Test: {len(test_ratings):,} ratings")
    
    return train_ratings, test_ratings


def load_users_data(data_dir: str) -> pd.DataFrame:
    """
    Load user data from u.user file.
    
    Parameters:
    -----------
    data_dir : str
        Directory containing MovieLens data files
    
    Returns:
    --------
    pd.DataFrame : Users dataframe
    """
    logger.info(f"Loading users data from {data_dir}")
    
    users = pd.read_csv(
        Path(data_dir) / 'u.user',
        sep='|',
        names=['user_id', 'age', 'gender', 'occupation', 'zip_code'],
        encoding='latin-1'
    )
    
    logger.info(f"Loaded {len(users)} users")
    logger.info(f"  Age range: {users['age'].min()} to {users['age'].max()}")
    
    return users
