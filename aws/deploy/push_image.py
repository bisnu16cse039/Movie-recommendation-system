#!/usr/bin/env python3
"""
Push Docker images to ECR
"""
import os
import sys
import subprocess
import base64
from pathlib import Path
from dotenv import load_dotenv
import boto3

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

def load_config():
    """Load configuration from aws-config.env"""
    config = {}
    config_file = project_root / 'aws-config.env'
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key] = value
    
    return config

def push_to_ecr():
    """Push Docker image to ECR"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    config = load_config()
    
    api_repo = config.get('MOVIE_RECSYS_API_REPO')
    account_id = config.get('AWS_ACCOUNT_ID')
    
    if not api_repo or not account_id:
        print("❌ Missing MOVIE_RECSYS_API_REPO or AWS_ACCOUNT_ID in aws-config.env")
        return False
    
    print("=" * 70)
    print("🐳 Pushing Docker Image to ECR")
    print("=" * 70)
    print(f"\n📋 Configuration:")
    print(f"   Region: {region}")
    print(f"   Account: {account_id}")
    print(f"   Repo: {api_repo}")
    
    # Get ECR login credentials
    print(f"\n🔐 Getting ECR authentication token...")
    
    try:
        ecr = boto3.client('ecr', region_name=region)
        response = ecr.get_authorization_token()
        
        auth_data = response['authorizationData'][0]
        token = base64.b64decode(auth_data['authorizationToken']).decode('utf-8')
        username, password = token.split(':')
        registry = auth_data['proxyEndpoint']
        
        print(f"   ✅ Got authentication token")
        
    except Exception as e:
        print(f"   ❌ Failed to get ECR token: {e}")
        return False
    
    # Docker login
    print(f"\n🔑 Logging into ECR...")
    
    try:
        result = subprocess.run(
            ['docker', 'login', '--username', username, '--password-stdin', registry],
            input=password.encode(),
            capture_output=True,
            text=False
        )
        
        if result.returncode != 0:
            print(f"   ❌ Docker login failed: {result.stderr.decode()}")
            return False
        
        print(f"   ✅ Docker logged in")
        
    except Exception as e:
        print(f"   ❌ Docker login error: {e}")
        return False
    
    # Check if local image exists
    print(f"\n🔍 Checking local Docker image...")
    
    try:
        result = subprocess.run(
            ['docker', 'images', '-q', 'movie-recsys-api:latest'],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            print(f"   ❌ Local image 'movie-recsys-api:latest' not found")
            print(f"\n   Build it first:")
            print(f"   docker build --target serving -t movie-recsys-api:latest .")
            return False
        
        print(f"   ✅ Local image found")
        
    except Exception as e:
        print(f"   ❌ Error checking image: {e}")
        return False
    
    # Tag image
    print(f"\n🏷️  Tagging image...")
    
    try:
        result = subprocess.run(
            ['docker', 'tag', 'movie-recsys-api:latest', f'{api_repo}:latest'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"   ❌ Tagging failed: {result.stderr}")
            return False
        
        print(f"   ✅ Tagged: {api_repo}:latest")
        
    except Exception as e:
        print(f"   ❌ Tagging error: {e}")
        return False
    
    # Push image
    print(f"\n⬆️  Pushing image to ECR (this may take a few minutes)...")
    
    try:
        result = subprocess.run(
            ['docker', 'push', f'{api_repo}:latest'],
            capture_output=False,  # Show progress
            text=True
        )
        
        if result.returncode != 0:
            print(f"   ❌ Push failed")
            return False
        
        print("\n" + "=" * 70)
        print("✅ Image Pushed Successfully!")
        print("=" * 70)
        print(f"\n📦 Image URI: {api_repo}:latest")
        print(f"\nNow deploy to ECS:")
        print(f"  source .venv/bin/activate && python3 src/utils/deploy_ecs.py")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Push error: {e}")
        return False

if __name__ == '__main__':
    try:
        success = push_to_ecr()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
