#!/usr/bin/env python3
"""Upload models to S3"""
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("📦 S3 Model Upload Script")
print("=" * 70)

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
env_file = project_root / '.env'
print(f"\n🔍 Loading .env file from: {env_file}")
print(f"   .env exists: {env_file.exists()}")

if not env_file.exists():
    print(f"\n❌ Error: .env file not found at {env_file}")
    print("💡 Please create .env file in project root")
    sys.exit(1)

load_dotenv(dotenv_path=env_file)

# Debug: Show what was loaded
print(f"\n🔍 Attempting to load environment variables...")
with open(env_file, 'r') as f:
    lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
    print(f"   Found {len(lines)} non-comment lines in .env")
    # Show first 3 variable names (not values)
    for line in lines[:3]:
        if '=' in line:
            key = line.split('=')[0]
            print(f"   - {key}=...")

# Verify environment variables
bucket = os.getenv("S3_BUCKET_NAME")
region = os.getenv("AWS_DEFAULT_REGION")
access_key = os.getenv("AWS_ACCESS_KEY_ID")

print(f"   S3_BUCKET_NAME: {bucket}")
print(f"   AWS_DEFAULT_REGION: {region}")
print(f"   AWS_ACCESS_KEY_ID: {'***' + access_key[-4:] if access_key and len(access_key) > 4 else 'NOT SET'}")

if not bucket:
    print("\n❌ Error: S3_BUCKET_NAME not set in .env file")
    print("💡 Please edit .env and set: S3_BUCKET_NAME=your-bucket-name")
    sys.exit(1)

if not access_key:
    print("\n❌ Error: AWS credentials not set")
    print("💡 Please edit .env and set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    print("💡 Or run: aws configure")
    sys.exit(1)

# Check if models exist
model_dir = Path('models/v1.0.0')
print(f"\n📁 Checking local models in: {model_dir}")
if not model_dir.exists():
    print(f"❌ Error: Directory {model_dir} does not exist")
    print("💡 Please run training first: python train_model.py")
    sys.exit(1)

model_files = list(model_dir.glob('*'))
print(f"   Found {len(model_files)} files:")
for f in model_files:
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"   - {f.name} ({size_mb:.2f} MB)")

# Upload
print(f"\n🚀 Uploading to S3 bucket: {bucket}")
print("-" * 70)

try:
    from src.utils.storage import upload_models_to_s3
    uploaded = upload_models_to_s3('v1.0.0', Path('models/v1.0.0'))
    
    print("\n" + "=" * 70)
    print(f'✅ SUCCESS: Uploaded {len(uploaded)} files')
    print("=" * 70)
    for uri in uploaded:
        print(f'  📄 {uri}')
    print("\n💡 Verify upload: aws s3 ls s3://{}/models/v1.0.0/".format(bucket))
    
except Exception as e:
    print("\n" + "=" * 70)
    print(f"❌ UPLOAD FAILED")
    print("=" * 70)
    print(f"Error: {e}")
    print("\n📋 Full traceback:")
    import traceback
    traceback.print_exc()
    print("\n💡 Troubleshooting:")
    print("  1. Check AWS credentials: aws sts get-caller-identity")
    print("  2. Check bucket exists: aws s3 ls s3://{}".format(bucket))
    print("  3. Check IAM permissions for s3:PutObject")
    sys.exit(1)