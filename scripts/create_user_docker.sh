#!/bin/bash
# Run create_user.py inside the Docker container

echo "Creating user in Docker container..."

# Check if container is running
if ! docker ps | grep -q rag-api; then
    echo "Error: rag-api container is not running"
    echo "Start it with: docker compose up -d"
    exit 1
fi

# Run the create_user script inside the container
docker exec -it rag-api python /app/scripts/create_user.py