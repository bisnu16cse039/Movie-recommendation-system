#!/bin/bash
# Push Docker images to ECR

set -e

echo "========================================================================"
echo "🐳 Pushing Docker Images to ECR"
echo "========================================================================"

# Load configuration
if [ ! -f "aws-config.env" ]; then
    echo "❌ aws-config.env not found"
    exit 1
fi

export $(cat aws-config.env | grep -v '^#' | xargs)
export $(cat .env | grep -v '^#' | grep 'AWS_' | xargs)

REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo ""
echo "📋 Configuration:"
echo "   Region: $REGION"
echo "   Account: $AWS_ACCOUNT_ID"
echo "   API Repo: $MOVIE_RECSYS_API_REPO"

# Authenticate Docker to ECR
echo ""
echo "🔐 Authenticating Docker with ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ Failed to authenticate with ECR"
    exit 1
fi

echo "   ✅ Authenticated"

# Check if local image exists
echo ""
echo "🔍 Checking local Docker image..."
if ! docker images | grep -q "movie-recsys-api"; then
    echo "❌ Local image 'movie-recsys-api' not found"
    echo "   Build it first: docker build --target serving -t movie-recsys-api ."
    exit 1
fi

echo "   ✅ Local image found"

# Tag image
echo ""
echo "🏷️  Tagging image..."
docker tag movie-recsys-api:latest $MOVIE_RECSYS_API_REPO:latest

# Push image
echo ""
echo "⬆️  Pushing image to ECR (this may take a few minutes)..."
docker push $MOVIE_RECSYS_API_REPO:latest

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ Image pushed successfully!"
    echo "========================================================================"
    echo ""
    echo "📦 Image URI: $MOVIE_RECSYS_API_REPO:latest"
    echo ""
    echo "Next step: Deploy to ECS"
    echo "  python3 src/utils/deploy_ecs.py"
else
    echo ""
    echo "❌ Failed to push image"
    exit 1
fi
