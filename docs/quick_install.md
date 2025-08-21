# RAG System Quick Install Guide

This guide provides the fastest way to get the RAG system up and running on Debian-based systems.

## Prerequisites

- Debian 11+ or Ubuntu 20.04+
- 8GB RAM minimum
- 50GB free disk space
- Internet connection

## Option 1: One-Line Docker Install (Fastest)

```bash
curl -fsSL https://raw.githubusercontent.com/mlewanca/_RAG_system/master/scripts/quick_install.sh | bash
```

This script will:
- Install Docker and Docker Compose
- Clone the repository
- Start all services
- Create an admin user
- Display access credentials

## Option 2: Manual Quick Install (5 minutes)

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Clone and Start

```bash
# Clone repository
git clone https://github.com/mlewanca/_RAG_system.git
cd _RAG_system

# Configure environment
cp .env.example .env
sed -i "s/your-secret-key-here-minimum-32-characters/$( openssl rand -base64 48 )/" .env

# Start services
docker compose up -d

# Wait for services to be ready
sleep 30

# Pull AI models
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull gemma3:27b
```

### Step 3: Create Admin User

```bash
# Create admin user
docker compose exec rag-api python src/create_user.py --batch \
  --username admin \
  --email admin@localhost \
  --role admin \
  --password "ChangeMe123!" \
  --full-name "Administrator"
```

### Step 4: Access the System

Open your browser and navigate to:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

Login with:
- Username: `admin`
- Password: `ChangeMe123!`

## Option 3: Development Quick Start

For developers who want to run the system locally:

```bash
# Clone and enter directory
git clone https://github.com/mlewanca/_RAG_system.git
cd _RAG_system

# Run development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access development tools
# - API: http://localhost:8000
# - Mailhog: http://localhost:8025
# - MinIO: http://localhost:9001
```

## Quick Test

Test the installation:

```bash
# Check health
curl http://localhost:8000/health

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ChangeMe123!"}' \
  | jq -r .access_token)

# Test query
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the RAG system?","max_results":3}'
```

## Common Commands

```bash
# View logs
docker compose logs -f

# Stop services
docker compose down

# Update system
git pull
docker compose pull
docker compose up -d

# Reset everything
docker compose down -v
rm -rf data/
docker compose up -d
```

## Troubleshooting Quick Fixes

### Services not starting?
```bash
docker compose down
docker system prune -f
docker compose up -d
```

### Out of memory?
```bash
# Check memory usage
docker stats

# Restart with limited resources
docker compose down
docker compose up -d --scale prometheus=0 --scale grafana=0
```

### Can't access the API?
```bash
# Check if services are running
docker compose ps

# Check logs for errors
docker compose logs rag-api

# Ensure ports are not in use
sudo lsof -i :8000
```

## Next Steps

1. **Change the default password** immediately
2. Review [security settings](debian_installation_guide.md#security-considerations)
3. Configure [monitoring](debian_installation_guide.md#performance-tuning)
4. Read the [API documentation](api_documentation.md)

## Need Help?

- Full installation guide: [debian_installation_guide.md](debian_installation_guide.md)
- Development setup: [development_setup.md](development_setup.md)
- GitHub Issues: https://github.com/mlewanca/_RAG_system/issues

---

**Note**: This quick install is for testing and development. For production deployments, please follow the [complete installation guide](debian_installation_guide.md) with proper security configurations.