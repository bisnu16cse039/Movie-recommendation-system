#!/bin/bash

# Stop all Docker services and optionally clean up volumes
# Usage: ./docker/stop.sh [--clean]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Stopping Movie Recommendation System${NC}"
echo -e "${BLUE}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Stop services
echo -e "${GREEN}Stopping all services...${NC}"
docker-compose down

echo -e "${GREEN}✅ Services stopped${NC}"

# Check for --clean flag
if [[ "$1" == "--clean" ]]; then
    echo -e "\n${YELLOW}Cleaning up volumes and images...${NC}"
    
    # Remove volumes
    echo -e "${YELLOW}Removing volumes...${NC}"
    docker volume rm recsys-models recsys-training-logs recsys-api-logs recsys-retraining-logs 2>/dev/null || true
    
    # Remove images
    echo -e "${YELLOW}Removing images...${NC}"
    docker rmi movie-recsys-builder:latest \
               movie-recsys-training:latest \
               movie-recsys-api:latest \
               movie-recsys-retraining:latest 2>/dev/null || true
    
    # Remove network
    docker network rm recsys-network 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
    echo -e "${YELLOW}Note: Models in ./models/ directory are preserved${NC}"
else
    echo -e "\n${GREEN}To clean up volumes and images, run:${NC}"
    echo -e "  ${YELLOW}./docker/stop.sh --clean${NC}"
fi

echo ""
