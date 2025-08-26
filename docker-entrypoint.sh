#!/bin/bash
set -e

# Ensure required directories exist with proper permissions
echo "Ensuring required directories exist..."

# Create directories if they don't exist
mkdir -p /data/logs /data/config /data/documents /data/chroma_db /data/backups /data/cache /data/temp

# Create static directory for Swagger UI (if needed)
mkdir -p /app/static/swagger

# Since we're running as raguser (uid 1000), we need to ensure we have write permissions
# The container will fail if it can't write to these directories
if [ ! -w /data/logs ]; then
    echo "Warning: /data/logs is not writable by current user"
    echo "Container may fail to start. Please ensure the host directory has proper permissions."
    echo "Run on host: sudo chown -R 1000:1000 ./data"
fi

# Execute the main command
exec "$@"