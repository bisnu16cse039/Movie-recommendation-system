#!/bin/bash

# Start Movie Recommendation System in development mode
# Usage: ./docker/start-dev.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Development Environment${NC}"
echo -e "${BLUE}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if models exist locally
if [ ! -d "models/v1.0.0" ] || [ ! -f "models/v1.0.0/cosine_similarity_matrix.pkl" ]; then
    echo -e "${YELLOW}⚠️  No pre-trained models found. Running training first...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm training
    echo -e "${GREEN}✅ Training completed!${NC}"
fi

# Start services in development mode
echo -e "\n${GREEN}Starting API service with live reload...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d api

# Wait for API to be ready
echo -e "\n${YELLOW}Waiting for API to be ready...${NC}"
sleep 5

# Check if API is responding
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is ready!${NC}"
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${GREEN}Development environment is running!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "\n${GREEN}Available endpoints:${NC}"
    echo -e "  API:           ${YELLOW}http://localhost:8000${NC}"
    echo -e "  Health check:  ${YELLOW}http://localhost:8000/health${NC}"
    echo -e "  API docs:      ${YELLOW}http://localhost:8000/docs${NC}"
    echo -e "  Metrics:       ${YELLOW}http://localhost:8000/metrics${NC}"
    echo -e "\n${GREEN}Useful commands:${NC}"
    echo -e "  View logs:     ${YELLOW}docker-compose logs -f api${NC}"
    echo -e "  Restart API:   ${YELLOW}docker-compose restart api${NC}"
    echo -e "  Stop services: ${YELLOW}./docker/stop.sh${NC}"
    echo -e "  Retrain model: ${YELLOW}./docker/train.sh${NC}"
else
    echo -e "${YELLOW}⚠️  API not responding yet. Check logs:${NC}"
    echo -e "  ${YELLOW}docker-compose logs api${NC}"
fi

echo ""
