"""FastAPI application for movie recommendations"""

from fastapi import FastAPI, HTTPException, Query, Path as PathParam, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.recommender import ContentBasedRecommender
from config.settings import Settings
from api.middleware import RequestLoggingMiddleware
from api.metrics import metrics_tracker

# Load configuration
settings = Settings.from_yaml()

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Starting application in {settings.environment} environment")

# Initialize FastAPI app
app = FastAPI(
    title="Movie Recommendation API",
    description="Content-based movie recommendation system using MovieLens 100k dataset",
    version=settings.model.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with config
if settings.cors.enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    logger.info(f"CORS enabled with origins: {settings.cors.origins}")

# Add logging and metrics middleware
app.add_middleware(RequestLoggingMiddleware)

# Global recommender instance (lazy loaded)
recommender: Optional[ContentBasedRecommender] = None


def get_recommender() -> ContentBasedRecommender:
    """Get or initialize recommender instance"""
    global recommender
    if recommender is None:
        logger.info("Initializing recommender...")
        model_path = settings.project_root / settings.model.artifacts_dir / settings.model.version
        recommender = ContentBasedRecommender(
            model_dir=str(model_path),
            similarity_method=settings.similarity.default_method,
            cache_size=128
        )
        logger.info("Recommender initialized successfully")
    return recommender


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class MovieRating(BaseModel):
    """Single movie rating"""
    movie_id: int = Field(..., ge=1, description="Movie ID (1-indexed)")
    rating: float = Field(..., ge=0.5, le=5.0, description="Rating (0.5 to 5.0)")


class RecommendationRequest(BaseModel):
    """Request model for personalized recommendations"""
    user_ratings: Dict[int, float] = Field(
        ...,
        description="User's movie ratings as {movie_id: rating}",
        example={1: 5.0, 50: 4.0, 121: 3.5}
    )
    n: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of recommendations to return"
    )
    min_rating: float = Field(
        default=3.5,
        ge=0.5,
        le=5.0,
        description="Minimum rating to consider as 'liked'"
    )
    
    @validator('user_ratings')
    def validate_ratings(cls, v):
        """Validate user ratings"""
        if not v:
            raise ValueError("user_ratings cannot be empty")
        
        for movie_id, rating in v.items():
            if not isinstance(movie_id, int) or movie_id < 1:
                raise ValueError(f"Invalid movie_id: {movie_id}")
            if not (0.5 <= rating <= 5.0):
                raise ValueError(f"Rating must be between 0.5 and 5.0, got {rating}")
        
        return v


class MovieInfo(BaseModel):
    """Movie information"""
    movie_id: int
    title: str
    year: Optional[int] = None


class RecommendedMovie(MovieInfo):
    """Recommended movie with predicted score"""
    predicted_score: float = Field(..., description="Predicted relevance score")


class SimilarMovie(MovieInfo):
    """Similar movie with similarity score"""
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")


class RecommendationResponse(BaseModel):
    """Response model for recommendations"""
    recommendations: List[RecommendedMovie]
    count: int
    request: Dict


class SimilarMoviesResponse(BaseModel):
    """Response model for similar movies"""
    query_movie: MovieInfo
    similar_movies: List[SimilarMovie]
    count: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    model_version: str
    timestamp: str
    loaded: bool
    cache_stats: Optional[Dict] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str


class MovieDetailResponse(BaseModel):
    """Detailed movie information"""
    movie_id: int
    title: str
    year: Optional[int]
    genres: List[str]
    imdb_url: Optional[str]


class SearchResponse(BaseModel):
    """Movie search response"""
    query: str
    results: List[MovieInfo]
    count: int


# ============================================================================
# API Endpoints
# ============================================================================

@app.get(
    "/",
    summary="Root endpoint",
    response_model=Dict,
    tags=["General"]
)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Movie Recommendation API",
        "version": settings.model.version,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "recommend": "POST /recommend",
            "similar": "GET /movies/{movie_id}/similar",
            "search": "GET /movies/search",
            "info": "GET /movies/{movie_id}"
        }
    }


@app.get(
    "/health",
    summary="Health check",
    response_model=HealthResponse,
    tags=["General"]
)
async def health_check():
    """
    Health check endpoint to verify API and model status.
    
    Returns:
    - status: "healthy" if operational
    - version: API version
    - model_version: Loaded model version
    - loaded: Whether model is loaded
    - cache_stats: Cache hit/miss statistics (if model loaded)
    """
    try:
        rec = get_recommender()
        loaded = True
        cache_stats = rec.get_cache_info()
        model_version = rec.metadata['model_version']
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        loaded = False
        cache_stats = None
        model_version = "not loaded"
    
    return HealthResponse(
        status="healthy" if loaded else "degraded",
        version=settings.model.version,
        model_version=model_version,
        timestamp=datetime.utcnow().isoformat(),
        loaded=loaded,
        cache_stats=cache_stats
    )


@app.post(
    "/recommend",
    summary="Get personalized recommendations",
    response_model=RecommendationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Recommendations"]
)
async def get_recommendations(request: RecommendationRequest):
    """
    Generate personalized movie recommendations based on user's rating history.
    
    **Algorithm:**
    1. Takes user's movie ratings as input
    2. Finds similar movies to those the user liked (rating >= min_rating)
    3. Aggregates similarity scores weighted by user ratings
    4. Returns top-N movies sorted by predicted relevance
    
    **Example request:**
    ```json
    {
        "user_ratings": {
            "1": 5.0,
            "50": 4.5,
            "121": 3.5
        },
        "n": 10,
        "min_rating": 3.5
    }
    ```
    """
    try:
        rec = get_recommender()
        
        # Generate recommendations
        recommendations = rec.get_recommendations(
            user_ratings=request.user_ratings,
            n=request.n,
            min_rating=request.min_rating
        )
        
        return RecommendationResponse(
            recommendations=[RecommendedMovie(**movie) for movie in recommendations],
            count=len(recommendations),
            request={
                "n_input_ratings": len(request.user_ratings),
                "n_recommendations": request.n,
                "min_rating": request.min_rating
            }
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


@app.get(
    "/movies/search",
    summary="Search movies by title",
    response_model=List[MovieInfo],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Movies"]
)
async def search_movies(
    q: str = Query(..., min_length=1, description="Search query (movie title)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search for movies by title (partial match, case-insensitive).
    
    Returns a list of movies matching the search query.
    
    **Example:** `/movies/search?q=toy%20story&limit=5`
    """
    try:
        rec = get_recommender()
        results = rec.search_movies(query=q, limit=limit)
        return [MovieInfo(**movie) for movie in results]
    
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.get(
    "/movies/{movie_id}/similar",
    summary="Get similar movies",
    response_model=SimilarMoviesResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Movie not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Recommendations"]
)
async def get_similar_movies(
    movie_id: int = PathParam(..., ge=1, description="Movie ID"),
    n: int = Query(default=10, ge=1, le=50, description="Number of similar movies")
):
    """
    Get movies similar to a given movie (item-to-item recommendations).
    
    Uses content-based similarity (genres + year) to find similar movies.
    Results are cached for faster repeated queries.
    
    **Example:** `/movies/1/similar?n=10`
    """
    try:
        rec = get_recommender()
        
        # Get movie info
        movie_info = rec.get_movie_info(movie_id)
        if movie_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found"
            )
        
        # Get similar movies
        similar_movies = rec.get_similar_movies(movie_id=movie_id, n=n)
        
        return SimilarMoviesResponse(
            query_movie=MovieInfo(
                movie_id=movie_info['movie_id'],
                title=movie_info['title'],
                year=movie_info['year']
            ),
            similar_movies=[SimilarMovie(**movie) for movie in similar_movies],
            count=len(similar_movies)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar movies error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get similar movies"
        )


@app.get(
    "/movies/{movie_id}",
    summary="Get movie details",
    response_model=MovieDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Movie not found"}
    },
    tags=["Movies"]
)
async def get_movie_details(
    movie_id: int = PathParam(..., ge=1, description="Movie ID")
):
    """
    Get detailed information about a specific movie.
    
    Returns:
    - Movie ID, title, year
    - List of genres
    - IMDb URL (if available)
    """
    try:
        rec = get_recommender()
        movie_info = rec.get_movie_info(movie_id)
        
        if movie_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found"
            )
        
        return MovieDetailResponse(**movie_info)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get movie error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get movie details"
        )


@app.get(
    "/movies/search",
    summary="Search movies",
    response_model=SearchResponse,
    tags=["Movies"]
)
async def search_movies(
    q: str = Query(..., min_length=1, description="Search query (movie title)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results")
):
    """
    Search for movies by title (case-insensitive partial match).
    
    **Example:** `/movies/search?q=toy+story&limit=5`
    """
    try:
        rec = get_recommender()
        results = rec.search_movies(query=q, limit=limit)
        
        return SearchResponse(
            query=q,
            results=[MovieInfo(**movie) for movie in results],
            count=len(results)
        )
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search movies"
        )


@app.post(
    "/cache/clear",
    summary="Clear cache",
    tags=["Admin"]
)
async def clear_cache():
    """
    Clear the LRU cache for similar movies.
    
    Use this if you've updated the model and want to invalidate cached results.
    """
    try:
        rec = get_recommender()
        old_stats = rec.get_cache_info()
        rec.clear_cache()
        
        return {
            "status": "success",
            "message": "Cache cleared",
            "previous_stats": old_stats
        }
    
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """Get application metrics
    
    Returns:
        dict: Current metrics including:
            - uptime_seconds: Application uptime
            - total_requests: Total number of requests processed
            - successful_requests: Number of successful requests (2xx-3xx)
            - failed_requests: Number of failed requests (4xx-5xx)
            - success_rate: Percentage of successful requests
            - avg_latency_ms: Average request latency in milliseconds
            - errors_by_type: Breakdown of errors by exception type
            - requests_by_endpoint: Request count per endpoint
            - status_codes: Request count per HTTP status code
    """
    return metrics_tracker.get_metrics()


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("="*80)
    logger.info("Movie Recommendation API - Starting")
    logger.info("="*80)
    logger.info(f"API Version: {settings.model.version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Model directory: {settings.model.artifacts_dir}/{settings.model.version}")
    logger.info("="*80)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Movie Recommendation API - Shutting down")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=True,
        log_level="info"
    )
