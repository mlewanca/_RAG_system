#!/bin/bash

# Download Swagger UI assets for offline use
echo "Downloading Swagger UI assets..."

cd static/swagger

# Download the essential Swagger UI files
curl -s -O https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js
curl -s -O https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css
curl -s -O https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js

echo "Swagger UI assets downloaded successfully!"