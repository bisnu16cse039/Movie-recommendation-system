#!/usr/bin/env python3
"""
Create ECR repositories for the Movie Recommendation System
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

def create_ecr_repositories():
    """Create ECR repositories for Docker images"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    repositories = [
        'movie-recsys/api',
        'movie-recsys/training',
        'movie-recsys/retraining'
    ]
    
    print(f"🔧 Creating ECR repositories in {region}...")
    print("=" * 70)
    
    ecr = boto3.client('ecr', region_name=region)
    repo_uris = {}
    
    for repo_name in repositories:
        try:
            response = ecr.create_repository(
                repositoryName=repo_name,
                imageScanningConfiguration={'scanOnPush': True},
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            uri = response['repository']['repositoryUri']
            print(f"✅ Created: {repo_name}")
            print(f"   URI: {uri}")
            repo_uris[repo_name] = uri
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'RepositoryAlreadyExistsException':
                # Get existing repository URI
                response = ecr.describe_repositories(repositoryNames=[repo_name])
                uri = response['repositories'][0]['repositoryUri']
                print(f"ℹ️  Exists: {repo_name}")
                print(f"   URI: {uri}")
                repo_uris[repo_name] = uri
            else:
                print(f"❌ Error creating {repo_name}: {e}")
                raise
    
    # Save configuration
    print("\n" + "=" * 70)
    print("📝 Saving configuration to aws-config.env...")
    
    with open(project_root / 'aws-config.env', 'w') as f:
        f.write("# AWS ECR Repository URIs\n")
        f.write(f"AWS_REGION={region}\n")
        f.write(f"S3_BUCKET_NAME={os.getenv('S3_BUCKET_NAME')}\n")
        f.write(f"AWS_ACCOUNT_ID={repo_uris[repositories[0]].split('.')[0]}\n\n")
        
        for repo_name, uri in repo_uris.items():
            var_name = repo_name.replace('/', '_').replace('-', '_').upper() + '_REPO'
            f.write(f"{var_name}={uri}\n")
    
    print("=" * 70)
    print("✅ ECR Setup Complete!")
    print(f"\n📋 Configuration saved to: aws-config.env")
    print("\nNext steps:")
    print("  1. Build Docker images: ./build.sh")
    print("  2. Push to ECR: ./push_to_ecr.sh")

if __name__ == '__main__':
    create_ecr_repositories()
