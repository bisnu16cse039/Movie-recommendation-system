#!/bin/bash

# Build Docker images for Movie Recommendation System
# Usage: ./docker/build.sh [--no-cache]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Building Movie Recommendation System${NC}"
echo -e "${BLUE}========================================${NC}"

# Parse arguments
NO_CACHE_FLAG=""
if [[ "$1" == "--no-cache" ]]; then
    NO_CACHE_FLAG="--no-cache"
    echo -e "${YELLOW}Building with --no-cache flag${NC}"
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Build all stages
echo -e "\n${GREEN}[1/4] Building base builder image...${NC}"
docker build $NO_CACHE_FLAG --target builder -t movie-recsys-builder:latest .

echo -e "\n${GREEN}[2/4] Building training image...${NC}"
docker build $NO_CACHE_FLAG --target training -t movie-recsys-training:latest .

echo -e "\n${GREEN}[3/4] Building API serving image...${NC}"
docker build $NO_CACHE_FLAG --target serving -t movie-recsys-api:latest .

echo -e "\n${GREEN}[4/4] Building retraining service image...${NC}"
docker build $NO_CACHE_FLAG --target retraining -t movie-recsys-retraining:latest .

# Display image sizes
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Build completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\n${GREEN}Image sizes:${NC}"
docker images | grep movie-recsys

echo -e "\n${GREEN}To start services:${NC}"
echo -e "  Production: ${YELLOW}docker-compose up -d${NC}"
echo -e "  Development: ${YELLOW}./docker/start-dev.sh${NC}"
