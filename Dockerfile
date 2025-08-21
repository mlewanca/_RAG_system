# Multi-stage build for RAG System
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY docs/requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 raguser && \
    mkdir -p /app /data && \
    chown -R raguser:raguser /app /data

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/raguser/.local

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=raguser:raguser . /app/

# Create necessary directories
RUN mkdir -p /data/{config,logs,documents,chroma_db,backups,cache,temp} && \
    chown -R raguser:raguser /data

# Switch to non-root user
USER raguser

# Add local bin to PATH
ENV PATH=/home/raguser/.local/bin:$PATH

# Environment variables
ENV BASE_DIR=/data \
    DOCUMENTS_DIR=/data/documents \
    CHROMA_DIR=/data/chroma_db \
    LOGS_DIR=/data/logs \
    PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "src.production_api:app", "--host", "0.0.0.0", "--port", "8000"]