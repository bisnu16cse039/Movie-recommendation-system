#!/bin/bash

# Build and start Movie Recommendation System in development mode
# This is a convenience script that combines build.sh and start-dev.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Build & Start Development Environment${NC}"
echo -e "${BLUE}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Step 1: Build images
echo -e "\n${GREEN}[Step 1/2] Building Docker images...${NC}"
./docker/build.sh

# Step 2: Start development environment
echo -e "\n${GREEN}[Step 2/2] Starting development environment...${NC}"
./docker/start-dev.sh

echo -e "\n${GREEN}✅ Build and start completed!${NC}"
