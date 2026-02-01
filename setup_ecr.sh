#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Creating ECR Repositories...${NC}"

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

REGION=${AWS_DEFAULT_REGION:-us-east-1}
REPOS=("movie-recsys/api" "movie-recsys/training" "movie-recsys/retraining")

for REPO in "${REPOS[@]}"; do
    echo -e "\n${BLUE}Creating repository: $REPO${NC}"
    
    aws ecr create-repository \
        --repository-name "$REPO" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        2>&1 | grep -q "RepositoryAlreadyExistsException" && \
        echo -e "${GREEN}✓ Repository already exists${NC}" || \
        echo -e "${GREEN}✓ Repository created${NC}"
done

echo -e "\n${BLUE}Getting repository URIs...${NC}"
echo "" > aws-config.env

for REPO in "${REPOS[@]}"; do
    URI=$(aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" --query 'repositories[0].repositoryUri' --output text)
    VAR_NAME=$(echo "$REPO" | tr '/' '_' | tr '[:lower:]' '[:upper:]')_REPO
    echo "$VAR_NAME=$URI"
    echo "$VAR_NAME=$URI" >> aws-config.env
done

echo -e "\n${GREEN}✅ ECR Setup Complete!${NC}"
echo -e "Configuration saved to: aws-config.env"
