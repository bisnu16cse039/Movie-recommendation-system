# Multi-stage Dockerfile for Movie Recommendation System
# Supports both training and API serving with external storage integration

# =============================================================================
# Stage 1: Base Builder - Install system dependencies and build tools
# =============================================================================
FROM python:3.10-slim as builder

# Install build dependencies for Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Training Stage - Generate model artifacts
# =============================================================================
FROM builder as training

WORKDIR /app

# Copy application code
COPY config/ ./config/
COPY src/ ./src/
COPY train_model.py .

# Copy dataset (ml-100k/)
# Note: In production, this could be downloaded from S3 instead
COPY ml-100k/ ./ml-100k/

# Create models directory
RUN mkdir -p models logs

# Set environment for training
ENV RECSYS_ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

# Run training to generate artifacts
RUN python train_model.py

# Verify artifacts were created
RUN ls -lh models/v1.0.0/ && \
    echo "Training completed successfully"

# =============================================================================
# Stage 3: API Serving - Lightweight production image
# =============================================================================
FROM python:3.10-slim as serving

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY config/ ./config/
COPY src/ ./src/
COPY api/ ./api/
COPY start_api.py .

# Copy pre-trained model artifacts from training stage
# For local deployment: this copies from training stage
# For production: these will be downloaded from S3 at runtime (see storage.py)
COPY --from=training /app/models/ ./models/

# Copy dataset metadata (needed for API)
COPY ml-100k/u.item ./ml-100k/u.item

# Create necessary directories
RUN mkdir -p logs

# Create non-root user for security
RUN groupadd -r recsys && useradd -r -g recsys -u 1000 recsys && \
    chown -R recsys:recsys /app

# Switch to non-root user
USER recsys

# Environment variables
ENV RECSYS_ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1
ENV RECSYS_API__HOST=0.0.0.0
ENV RECSYS_API__PORT=8000
ENV RECSYS_API__RELOAD=false

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: start API server
CMD ["python", "start_api.py"]

# =============================================================================
# Stage 4: Training Service - For retraining scheduler
# =============================================================================
FROM builder as retraining

WORKDIR /app

# Copy application code
COPY config/ ./config/
COPY src/ ./src/
COPY train_model.py .

# Install cron for scheduled retraining
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p models logs ml-100k

# Create non-root user
RUN groupadd -r recsys && useradd -r -g recsys -u 1000 recsys && \
    chown -R recsys:recsys /app

# Environment variables
ENV RECSYS_ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

# Create cron job script
RUN echo '#!/bin/bash\n\
cd /app\n\
echo "Starting scheduled retraining at $(date)"\n\
python train_model.py >> /app/logs/retraining.log 2>&1\n\
echo "Retraining completed at $(date)"\n\
' > /app/retrain.sh && chmod +x /app/retrain.sh

# Create crontab (runs weekly on Sunday at 2 AM)
RUN echo "0 2 * * 0 /app/retrain.sh" > /etc/cron.d/retraining && \
    chmod 0644 /etc/cron.d/retraining && \
    crontab -u recsys /etc/cron.d/retraining

# Switch to non-root user for cron
USER recsys

# Default command: run cron in foreground OR manual training
CMD ["cron", "-f"]
