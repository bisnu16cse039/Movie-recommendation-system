"""Similarity computation for recommendation system"""

import numpy as np
import time
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SimilarityComputer:
    """Compute and store similarity matrices for movies"""
    
    SUPPORTED_METHODS = ['cosine', 'jaccard']
    
    def __init__(self):
        """Initialize similarity computer"""
        self.similarity_matrices: Dict[str, np.ndarray] = {}
        self.feature_matrix: Optional[np.ndarray] = None
        self.genre_columns: Optional[list] = None
        
    def compute_cosine_similarity(self, feature_matrix: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity matrix.
        
        Parameters:
        -----------
        feature_matrix : np.ndarray
            Feature matrix of shape (n_movies, n_features)
        
        Returns:
        --------
        np.ndarray : Similarity matrix of shape (n_movies, n_movies)
        """
        logger.info("Computing cosine similarity matrix...")
        start_time = time.time()
        
        similarity_matrix = cosine_similarity(feature_matrix)
        
        elapsed = time.time() - start_time
        
        logger.info(f"Cosine similarity computed in {elapsed:.3f}s")
        logger.info(f"  Matrix shape: {similarity_matrix.shape}")
        logger.info(f"  Value range: [{similarity_matrix.min():.4f}, {similarity_matrix.max():.4f}]")
        logger.info(f"  Mean similarity: {similarity_matrix.mean():.4f}")
        logger.info(f"  Memory size: {similarity_matrix.nbytes / (1024**2):.2f} MB")
        
        return similarity_matrix
    
    def compute_jaccard_similarity(
        self,
        genre_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Compute Jaccard similarity matrix (genre-only).
        
        Parameters:
        -----------
        genre_matrix : np.ndarray
            Binary genre matrix of shape (n_movies, n_genres)
        
        Returns:
        --------
        np.ndarray : Similarity matrix of shape (n_movies, n_movies)
        """
        logger.info("Computing Jaccard similarity matrix (genre-only)...")
        start_time = time.time()
        
        n_movies = genre_matrix.shape[0]
        similarity_matrix = np.zeros((n_movies, n_movies))
        
        # Compute Jaccard similarity for binary features
        for i in range(n_movies):
            for j in range(i, n_movies):
                # Calculate intersection and union
                intersection = np.sum(np.logical_and(genre_matrix[i], genre_matrix[j]))
                union = np.sum(np.logical_or(genre_matrix[i], genre_matrix[j]))
                
                # Jaccard similarity
                if union > 0:
                    similarity = intersection / union
                else:
                    similarity = 0.0
                
                # Symmetric matrix
                similarity_matrix[i, j] = similarity
                similarity_matrix[j, i] = similarity
        
        elapsed = time.time() - start_time
        
        logger.info(f"Jaccard similarity computed in {elapsed:.3f}s")
        logger.info(f"  Matrix shape: {similarity_matrix.shape}")
        logger.info(f"  Value range: [{similarity_matrix.min():.4f}, {similarity_matrix.max():.4f}]")
        logger.info(f"  Mean similarity: {similarity_matrix.mean():.4f}")
        
        return similarity_matrix
    
    def compute_all_similarities(
        self,
        feature_matrix: np.ndarray,
        genre_columns: list,
        movies_features: 'pd.DataFrame',
        methods: list = None
    ) -> Dict[str, np.ndarray]:
        """
        Compute all similarity matrices.
        
        Parameters:
        -----------
        feature_matrix : np.ndarray
            Full feature matrix (genres + normalized year)
        genre_columns : list
            List of genre column names
        movies_features : pd.DataFrame
            Movies dataframe with features
        methods : list, optional
            List of methods to compute. If None, computes all supported methods.
        
        Returns:
        --------
        Dict[str, np.ndarray] : Dictionary of similarity matrices by method name
        """
        if methods is None:
            methods = self.SUPPORTED_METHODS
        
        logger.info(f"Computing similarity matrices for methods: {methods}")
        
        self.feature_matrix = feature_matrix
        self.genre_columns = genre_columns
        
        # Compute each requested method
        for method in methods:
            if method == 'cosine':
                self.similarity_matrices['cosine'] = self.compute_cosine_similarity(
                    feature_matrix
                )
            elif method == 'jaccard':
                # Extract genre-only matrix for Jaccard
                genre_matrix = movies_features[genre_columns].values
                self.similarity_matrices['jaccard'] = self.compute_jaccard_similarity(
                    genre_matrix
                )
            else:
                logger.warning(f"Unknown similarity method: {method}")
        
        logger.info(f"Computed {len(self.similarity_matrices)} similarity matrices")
        
        return self.similarity_matrices
    
    def get_similarity_matrix(self, method: str = 'cosine') -> np.ndarray:
        """
        Get similarity matrix for a specific method.
        
        Parameters:
        -----------
        method : str
            Similarity method name
        
        Returns:
        --------
        np.ndarray : Similarity matrix
        """
        if method not in self.similarity_matrices:
            raise ValueError(f"Similarity matrix for method '{method}' not computed")
        
        return self.similarity_matrices[method]
