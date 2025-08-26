#!/bin/bash

# Script to fix permissions for Docker volumes
# Run this on the host machine before starting the containers

echo "Fixing permissions for RAG System Docker volumes..."

# Create data directories if they don't exist
mkdir -p ./data/{logs,config,documents,chroma_db,backups,cache,temp}

# Set ownership to UID 1000 (raguser in container)
# This ensures the container user can write to these directories
sudo chown -R 1000:1000 ./data

# Set proper permissions
sudo chmod -R 755 ./data

echo "Permissions fixed!"
echo ""
echo "You can now run: docker compose up -d"
echo ""
echo "If you still encounter permission issues, try:"
echo "  sudo chmod -R 777 ./data/logs"