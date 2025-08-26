# Using External Ollama with RAG System

This guide explains how to configure the RAG system to use an external Ollama instance instead of the bundled Docker container.

## Overview

The RAG system has been updated to support external Ollama instances. This allows you to:
- Use a single Ollama instance for multiple applications
- Run Ollama on a different machine or server
- Use GPU-accelerated Ollama on the host machine
- Reduce Docker resource usage

## Prerequisites

1. Ollama must be installed and running on your host machine or external server
2. Required models must be downloaded:
   ```bash
   ollama pull nomic-embed-text
   ollama pull gemma3:27b
   ollama pull qwen3:30b
   ```

## Installation Options

### Option 1: Install Ollama on Host Machine

#### Windows
```bash
# Download from https://ollama.ai/download/windows
# Or use winget:
winget install Ollama.Ollama
```

#### macOS
```bash
brew install ollama
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Option 2: Use Existing Ollama Server

If you have Ollama running on another machine, ensure it's accessible from the Docker host.

## Configuration

### 1. Set the OLLAMA_BASE_URL

Edit your `.env` file:

```bash
# For Windows/Mac Docker Desktop (Ollama on host)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# For Linux Docker (Ollama on host)
OLLAMA_BASE_URL=http://172.17.0.1:11434

# For external Ollama server
OLLAMA_BASE_URL=http://your-ollama-server:11434
```

### 2. Start Ollama

Ensure Ollama is running before starting the RAG system:

```bash
# Start Ollama service
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### 3. Start the RAG System

```bash
docker compose up -d
```

## Troubleshooting

### Connection Issues

1. **Docker Desktop (Windows/Mac)**:
   - Use `http://host.docker.internal:11434`
   - This special hostname resolves to the host machine

2. **Linux Docker**:
   - Use the Docker bridge IP: `http://172.17.0.1:11434`
   - Or use your host machine's actual IP address
   - Find Docker bridge IP: `docker network inspect bridge | grep Gateway`

3. **Firewall Issues**:
   - Ensure port 11434 is accessible
   - For external servers, check firewall rules

### Model Availability

Ensure all required models are downloaded on the Ollama instance:

```bash
# List available models
ollama list

# Pull missing models
ollama pull nomic-embed-text
ollama pull gemma3:27b
ollama pull qwen3:30b
```

### Performance Considerations

1. **Network Latency**: External Ollama may introduce latency
2. **GPU Access**: Host Ollama can use GPU acceleration
3. **Resource Sharing**: Multiple applications can share models

## Security Notes

1. **Local Network Only**: Only expose Ollama on trusted networks
2. **Authentication**: Ollama doesn't have built-in authentication
3. **Firewall Rules**: Restrict access to Ollama port (11434)

## Reverting to Docker Ollama

To revert to the bundled Ollama container, use the original docker-compose file or restore from git:

```bash
git checkout docker-compose.yml
docker compose up -d
```