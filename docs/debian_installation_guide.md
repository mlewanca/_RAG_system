# Enhanced LangChain RAG System - Debian Installation Guide

## Table of Contents
- [Debian-Specific Requirements](#debian-specific-requirements)
- [Installation Methods](#installation-methods)
  - [Method 1: Docker Installation (Recommended)](#method-1-docker-installation-recommended)
  - [Method 2: Native Installation](#method-2-native-installation)
- [Quick Start Guide](#quick-start-guide)
- [Troubleshooting](#troubleshooting-debian-specific-issues)

## Debian-Specific Requirements

### Supported Debian Versions
- **Debian 12 (Bookworm)** - Recommended
- **Debian 11 (Bullseye)** - Supported
- **Ubuntu 22.04 LTS** - Supported (Debian-based)
- **Ubuntu 20.04 LTS** - Supported with backports

### Minimum System Requirements
- **CPU**: 4 cores (8+ recommended)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB minimum (100GB+ recommended for models)
- **GPU**: Optional but recommended for better performance

## Installation Methods

You can install the RAG system using either Docker (recommended for ease) or native installation (recommended for production).

---

## Method 1: Docker Installation (Recommended)

Docker provides the easiest way to get the RAG system up and running with all dependencies properly configured.

### 1.1 Install Docker and Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 1.2 Clone the Repository

```bash
# Clone the RAG system repository
git clone https://github.com/mlewanca/_RAG_system.git
cd _RAG_system

# Create necessary directories
mkdir -p data/{config,logs,documents,chroma_db,backups}
```

### 1.3 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate secure JWT secret
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')

# Update .env file
sed -i "s/your-secret-key-here-minimum-32-characters-long/$JWT_SECRET/" .env

# Adjust other settings as needed
nano .env
```

### 1.4 Start with Docker Compose

```bash
# Pull and start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Pull Ollama models
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull gemma3:27b
docker compose exec ollama ollama pull qwen3:30b
```

### 1.5 Create Initial User

```bash
# Access the container
docker compose exec rag-api bash

# Create admin user
python src/create_user.py --batch \
  --username admin \
  --email admin@example.com \
  --role admin \
  --password "YourSecurePassword123!" \
  --full-name "System Administrator"

# Exit container
exit
```

### 1.6 Access the System

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Grafana** (monitoring): http://localhost:3000
- **Prometheus**: http://localhost:9090

### 1.7 Docker Management Commands

```bash
# Stop all services
docker compose down

# Start services
docker compose up -d

# Update services
git pull
docker compose pull
docker compose up -d

# View resource usage
docker stats

# Clean up unused resources
docker system prune -a
```

---

## Method 2: Native Installation

For production deployments or when you need more control over the system.

### 2.1 System Preparation

#### Update System
```bash
# Update package lists and system
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential curl wget git software-properties-common
```

#### Python 3.11 Installation
```bash
# For Debian 12 (Bookworm)
sudo apt install -y python3.11 python3.11-dev python3.11-venv python3-pip

# For Debian 11 (Bullseye) - Add backports
echo "deb http://deb.debian.org/debian bullseye-backports main" | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update
sudo apt install -y -t bullseye-backports python3.11 python3.11-dev python3.11-venv

# Set Python 3.11 as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --config python3

# Verify installation
python3 --version
```

### 2.2 Install System Dependencies

```bash
# Essential packages
sudo apt install -y \
    curl \
    git \
    nginx \
    redis-server \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    sqlite3 \
    libsqlite3-dev
```

### 2.3 Install Ollama

```bash
# Official installation
curl -fsSL https://ollama.com/install.sh | sh

# Create systemd service
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ollama
Group=ollama
WorkingDirectory=/var/lib/ollama
Environment="HOME=/var/lib/ollama"
Environment="OLLAMA_HOST=0.0.0.0:11434"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Create ollama user
sudo useradd -r -s /bin/false -m -d /var/lib/ollama ollama

# Start service
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull models
ollama pull nomic-embed-text
ollama pull gemma3:27b
ollama pull qwen3:30b
```

### 2.4 Clone and Setup Project

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/mlewanca/_RAG_system.git rag-system
sudo chown -R $USER:$USER /opt/rag-system
cd /opt/rag-system

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r docs/requirements.txt
```

### 2.5 Configure the System

```bash
# Create data directories
sudo mkdir -p /var/lib/rag-system/{documents,chroma_db,logs,backups,cache}
sudo chown -R $USER:$USER /var/lib/rag-system

# Setup environment
cp .env.example .env

# Generate secure JWT secret
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')
sed -i "s/your-secret-key-here-minimum-32-characters-long/$JWT_SECRET/" .env

# Update paths in .env
sed -i "s|/path/to/your/rag/data|/var/lib/rag-system|g" .env
```

### 2.6 Setup Nginx

```bash
# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Copy nginx configuration
sudo cp nginx/nginx.conf /etc/nginx/sites-available/rag-system

# Create self-signed certificate (for testing)
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Enable site
sudo ln -s /etc/nginx/sites-available/rag-system /etc/nginx/sites-enabled/

# Test and restart nginx
sudo nginx -t
sudo systemctl restart nginx
```

### 2.7 Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/rag-api.service > /dev/null <<EOF
[Unit]
Description=RAG System API
After=network.target ollama.service redis.service
Requires=ollama.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/rag-system
Environment="PATH=/opt/rag-system/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/rag-system/venv/bin/python -m uvicorn src.production_api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable rag-api
sudo systemctl start rag-api
```

### 2.8 Initialize the System

```bash
# Activate virtual environment
cd /opt/rag-system
source venv/bin/activate

# Setup directories
python scripts/setup_directories.py

# Create initial admin user
python src/create_user.py
```

---

## Quick Start Guide

For a quick installation, see the [Quick Install Guide](quick_install.md).

---

## Docker vs Native Installation Comparison

| Feature | Docker | Native |
|---------|--------|--------|
| Setup Time | ~10 minutes | ~30 minutes |
| Complexity | Low | Medium |
| Resource Overhead | ~5-10% | Minimal |
| Scalability | Excellent | Good |
| Update Process | Simple | Manual |
| Customization | Limited | Full |
| Production Ready | Yes | Yes |

---

## Troubleshooting Debian-Specific Issues

### Docker Issues

```bash
# Permission denied errors
sudo usermod -aG docker $USER
newgrp docker

# Clean up Docker resources
docker system prune -a --volumes

# Reset Docker
sudo systemctl restart docker
```

### Python Issues

```bash
# Module not found errors
source venv/bin/activate
pip install -r docs/requirements.txt

# SSL certificate errors
pip install --upgrade certifi
export SSL_CERT_FILE=$(python -m certifi)
```

### Service Issues

```bash
# Check all services
sudo systemctl status rag-api ollama nginx redis

# View logs
sudo journalctl -u rag-api -f
docker compose logs -f

# Restart services
sudo systemctl restart rag-api
docker compose restart
```

### Network Issues

```bash
# Check port availability
sudo netstat -tlnp | grep -E ':(80|443|8000|11434)'

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:11434/api/tags
```

---

## Security Considerations

1. **Firewall Configuration**
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

2. **SSL/TLS Setup**
   - Use Let's Encrypt for production
   - Configure nginx with proper SSL settings

3. **Regular Updates**
   ```bash
   # System updates
   sudo apt update && sudo apt upgrade

   # Docker updates
   docker compose pull
   docker compose up -d
   ```

---

## Performance Tuning

### System Optimization
```bash
# Increase file limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize kernel parameters
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Docker Optimization
```yaml
# In docker-compose.yml, add resource limits:
services:
  rag-api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

---

## Next Steps

1. Review the [API Documentation](api_documentation.md)
2. Configure monitoring with Grafana
3. Set up automated backups
4. Implement SSL certificates for production
5. Configure log aggregation

For additional help, refer to the [Development Setup Guide](development_setup.md) or create an issue on GitHub.