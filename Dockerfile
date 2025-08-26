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

# Install smaller dependencies first
RUN pip install --user --no-cache-dir \
    langchain==0.3.* \
    langchain-community>=0.0.20 \
    langchain-ollama>=0.1.0 \
    pypdf>=4.0.0 \
    pillow>=10.0.0 \
    chromadb>=0.4.0 \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    python-multipart>=0.0.6 \
    passlib[bcrypt]>=1.7.4 \
    python-jose[cryptography]>=3.3.0 \
    cryptography>=41.0.0 \
    bcrypt>=4.0.0 \
    pyjwt>=2.8.0 \
    email-validator>=2.1.0 \
    slowapi>=0.1.9 \
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    psutil>=5.9.0 \
    prometheus-client>=0.19.0 \
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0 \
    structlog>=23.0.0 \
    rich>=13.0.0 \
    tqdm>=4.66.0 \
    distro>=1.8.0

# Install PyTorch separately with retry
RUN pip install --user --no-cache-dir --default-timeout=1000 \
    --index-url https://download.pytorch.org/whl/cpu \
    torch>=2.0.0 \
    torchvision>=0.15.0

# Install remaining dependencies
RUN pip install --user --no-cache-dir \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    httpx>=0.25.0 \
    python-magic>=0.4.27 \
    python-docx>=0.8.11 \
    openpyxl>=3.1.0 \
    xlsxwriter>=3.1.0 \
    psycopg2-binary>=2.9.0 \
    sqlalchemy>=2.0.0

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

# Copy and set up entrypoint
COPY --chown=raguser:raguser docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

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

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command
CMD ["python", "-m", "uvicorn", "src.production_api:app", "--host", "0.0.0.0", "--port", "8000"]
