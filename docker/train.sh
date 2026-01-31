#!/bin/bash

# Trigger manual model retraining
# Usage: ./docker/train.sh [dev|prod]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

MODE="${1:-dev}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Manual Model Retraining (${MODE} mode)${NC}"
echo -e "${BLUE}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ "$MODE" == "dev" ]; then
    echo -e "${GREEN}Running training in development mode...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm retraining python train_model.py
elif [ "$MODE" == "prod" ]; then
    echo -e "${GREEN}Running training in production mode...${NC}"
    docker-compose run --rm retraining python train_model.py
else
    echo -e "${YELLOW}Invalid mode. Use 'dev' or 'prod'${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Retraining completed!${NC}"
echo -e "${YELLOW}Note: Restart the API service to load new models:${NC}"
echo -e "  ${YELLOW}docker-compose restart api${NC}"
