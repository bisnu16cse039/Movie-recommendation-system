"""
S3 Storage Utility for Model Artifacts
For production deployments with external model storage

Requirements:
    pip install boto3

Environment Variables:
    AWS_ACCESS_KEY_ID        - AWS access key
    AWS_SECRET_ACCESS_KEY    - AWS secret key
    AWS_DEFAULT_REGION       - AWS region (default: us-east-1)
    S3_BUCKET_NAME          - S3 bucket for model artifacts
    S3_MODEL_PREFIX         - Prefix/folder in bucket (default: models/)
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
import json
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. S3 storage functionality disabled.")


class S3Storage:
    """Handle model artifact storage in S3"""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        prefix: str = "models/",
        region: str = "us-east-1"
    ):
        """
        Initialize S3 storage client
        
        Args:
            bucket_name: S3 bucket name (or set S3_BUCKET_NAME env var)
            prefix: Folder prefix for artifacts (default: models/)
            region: AWS region (default: us-east-1)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3 storage. Install: pip install boto3")
        
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("bucket_name must be provided or S3_BUCKET_NAME env var must be set")
        
        self.prefix = prefix
        self.region = region
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            raise
    
    def upload_artifact(
        self,
        local_path: Path,
        s3_key: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a model artifact to S3
        
        Args:
            local_path: Path to local file
            s3_key: S3 key (defaults to filename with prefix)
            metadata: Optional metadata to attach to S3 object
            
        Returns:
            S3 URI of uploaded object
        """
        local_path = Path(local_path)
        
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        # Generate S3 key
        if s3_key is None:
            s3_key = f"{self.prefix}{local_path.name}"
        
        # Prepare metadata
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
        
        try:
            logger.info(f"Uploading {local_path.name} to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"✅ Upload successful: {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Failed to upload {local_path.name}: {e}")
            raise
    
    def download_artifact(
        self,
        s3_key: str,
        local_path: Path,
        overwrite: bool = False
    ) -> Path:
        """
        Download a model artifact from S3
        
        Args:
            s3_key: S3 key of the object
            local_path: Path to save downloaded file
            overwrite: Whether to overwrite existing file
            
        Returns:
            Path to downloaded file
        """
        local_path = Path(local_path)
        
        # Check if file already exists
        if local_path.exists() and not overwrite:
            logger.info(f"File already exists: {local_path}")
            return local_path
        
        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Downloading s3://{self.bucket_name}/{s3_key} to {local_path}")
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            logger.info(f"✅ Download successful: {local_path}")
            return local_path
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.error(f"Object not found in S3: s3://{self.bucket_name}/{s3_key}")
            else:
                logger.error(f"Failed to download {s3_key}: {e}")
            raise
    
    def upload_model_version(
        self,
        local_model_dir: Path,
        version: str,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Upload an entire model version directory to S3
        
        Args:
            local_model_dir: Path to local model directory (e.g., models/v1.0.0/)
            version: Model version (e.g., v1.0.0)
            exclude_patterns: File patterns to exclude (e.g., ['*.csv', 'temp_*'])
            
        Returns:
            List of S3 URIs for uploaded files
        """
        local_model_dir = Path(local_model_dir)
        exclude_patterns = exclude_patterns or []
        
        if not local_model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {local_model_dir}")
        
        uploaded_uris = []
        
        # Upload all files in directory
        for file_path in local_model_dir.iterdir():
            if file_path.is_file():
                # Check exclusions
                if any(file_path.match(pattern) for pattern in exclude_patterns):
                    logger.info(f"Skipping excluded file: {file_path.name}")
                    continue
                
                # Upload file
                s3_key = f"{self.prefix}{version}/{file_path.name}"
                s3_uri = self.upload_artifact(
                    file_path,
                    s3_key=s3_key,
                    metadata={
                        'version': version,
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                )
                uploaded_uris.append(s3_uri)
        
        logger.info(f"✅ Uploaded {len(uploaded_uris)} files for version {version}")
        return uploaded_uris
    
    def download_model_version(
        self,
        version: str,
        local_model_dir: Path,
        required_files: Optional[List[str]] = None
    ) -> Path:
        """
        Download an entire model version from S3
        
        Args:
            version: Model version (e.g., v1.0.0)
            local_model_dir: Path to save model files
            required_files: List of required filenames (optional validation)
            
        Returns:
            Path to local model directory
        """
        local_model_dir = Path(local_model_dir)
        local_model_dir.mkdir(parents=True, exist_ok=True)
        
        # List all objects with version prefix
        prefix = f"{self.prefix}{version}/"
        
        try:
            logger.info(f"Listing objects in s3://{self.bucket_name}/{prefix}")
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                raise FileNotFoundError(f"No objects found for version {version}")
            
            # Download each file
            downloaded_files = []
            for obj in response['Contents']:
                s3_key = obj['Key']
                filename = Path(s3_key).name
                local_path = local_model_dir / filename
                
                self.download_artifact(s3_key, local_path)
                downloaded_files.append(filename)
            
            # Validate required files
            if required_files:
                missing_files = set(required_files) - set(downloaded_files)
                if missing_files:
                    raise FileNotFoundError(
                        f"Missing required files: {missing_files}"
                    )
            
            logger.info(f"✅ Downloaded {len(downloaded_files)} files to {local_model_dir}")
            return local_model_dir
            
        except ClientError as e:
            logger.error(f"Failed to download model version {version}: {e}")
            raise
    
    def list_versions(self) -> List[str]:
        """
        List all model versions in S3
        
        Returns:
            List of version strings (e.g., ['v1.0.0', 'v1.1.0'])
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix,
                Delimiter='/'
            )
            
            versions = []
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    # Extract version from prefix (e.g., models/v1.0.0/ -> v1.0.0)
                    version = prefix['Prefix'].rstrip('/').split('/')[-1]
                    versions.append(version)
            
            logger.info(f"Found {len(versions)} versions in S3")
            return sorted(versions)
            
        except ClientError as e:
            logger.error(f"Failed to list versions: {e}")
            raise


def download_models_from_s3(
    version: str,
    local_dir: Path,
    bucket_name: Optional[str] = None
) -> Path:
    """
    Helper function to download model artifacts from S3
    Call this during API startup if models don't exist locally
    
    Args:
        version: Model version to download
        local_dir: Local directory to save models
        bucket_name: S3 bucket name (optional)
        
    Returns:
        Path to downloaded model directory
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available. Skipping S3 download.")
        return local_dir
    
    storage = S3Storage(bucket_name=bucket_name)
    
    required_files = [
        'cosine_similarity_matrix.pkl',
        'movies_features.pkl',
        'metadata.json'
    ]
    
    return storage.download_model_version(
        version=version,
        local_model_dir=local_dir,
        required_files=required_files
    )


def upload_models_to_s3(
    version: str,
    local_dir: Path,
    bucket_name: Optional[str] = None
) -> List[str]:
    """
    Helper function to upload model artifacts to S3
    Call this after training completes
    
    Args:
        version: Model version
        local_dir: Local directory containing model files
        bucket_name: S3 bucket name (optional)
        
    Returns:
        List of S3 URIs for uploaded files
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available. Skipping S3 upload.")
        return []
    
    storage = S3Storage(bucket_name=bucket_name)
    
    # Exclude CSV files to save space
    return storage.upload_model_version(
        local_model_dir=local_dir,
        version=version,
        exclude_patterns=['*.csv']
    )


if __name__ == "__main__":
    # Example usage
    import sys
    
    if not BOTO3_AVAILABLE:
        print("boto3 not installed. Install: pip install boto3")
        sys.exit(1)
    
    # Test connection
    try:
        storage = S3Storage()
        versions = storage.list_versions()
        print(f"Available versions: {versions}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
