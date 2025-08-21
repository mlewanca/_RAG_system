# Enhanced LangChain RAG System - Debian Installation Guide

## Debian-Specific Requirements

### Supported Debian Versions
- **Debian 12 (Bookworm)** - Recommended
- **Debian 11 (Bullseye)** - Supported
- **Ubuntu 22.04 LTS** - Supported (Debian-based)
- **Ubuntu 20.04 LTS** - Supported with backports

## Quick Installation for Debian

### 1. System Preparation

#### Update System
```bash
# Update package lists and system
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential curl wget git software-properties-common
```

#### Python 3.12 Installation on Debian
```bash
# For Debian 12 (Bookworm) - Python 3.12 available
sudo apt install -y python3.12 python3.12-dev python3.12-venv python3-pip

# For Debian 11 (Bullseye) - Add backports
echo "deb http://deb.debian.org/debian bullseye-backports main" | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update
sudo apt install -y python3.12 python3.12-dev python3.12-venv python3-pip

# Alternative: Use deadsnakes PPA (for older versions)
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa  # Ubuntu/derivatives only
sudo apt update
sudo apt install -y python3.12 python3.12-dev python3.12-venv python3.12-distutils

# Install pip for Python 3.12
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
```

#### Set Python 3.12 as Default (Optional)
```bash
# Create alternatives for python3
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 2

# Set python3.12 as default
sudo update-alternatives --config python3

# Verify installation
python3 --version  # Should show Python 3.12.x
```

### 2. Install System Dependencies

#### Core Dependencies
```bash
# Essential packages for Debian
sudo apt install -y \
    curl \
    git \
    nginx \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    python3.12-dev \
    python3.12-venv \
    python3-pip \
    sqlite3 \
    libsqlite3-dev
```

#### GPU Support (NVIDIA)
```bash
# Install NVIDIA drivers (if not already installed)
# Check available drivers
sudo apt search nvidia-driver

# Install recommended driver (adjust version as needed)
sudo apt install -y nvidia-driver-525 nvidia-utils-525

# Install CUDA (if needed for advanced GPU operations)
wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-2

# Reboot after driver installation
sudo reboot
```

### 3. Python Environment Setup

#### Create Virtual Environment (Recommended)
```bash
# Create project directory
sudo mkdir -p /nvme0n1p2
sudo chown $USER:$USER /nvme0n1p2
cd /nvme0n1p2

# Create virtual environment
python3.12 -m venv rag-env
source rag-env/bin/activate

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel
```

#### Install Python Dependencies
```bash
# Activate virtual environment
source /nvme0n1p2/rag-env/bin/activate

# Core dependencies
pip install --upgrade \
    langchain==0.3 \
    langchain-community \
    langchain-ollama \
    pypdf \
    unstructured[pdf] \
    chromadb \
    tqdm \
    pillow \
    fastapi \
    uvicorn \
    pandas \
    torch \
    torchvision \
    psutil \
    prometheus-client \
    pydantic-settings \
    structlog \
    rich

# Security packages (REQUIRED)
pip install --upgrade \
    passlib[bcrypt] \
    python-jose[cryptography] \
    python-multipart \
    cryptography \
    bcrypt \
    pyjwt \
    email-validator \
    slowapi

# Additional Debian-specific packages
pip install --upgrade \
    python-apt \
    distro
```

### 4. Ollama Installation for Debian

#### Install Ollama
```bash
# Official installation
curl -fsSL https://ollama.com/install.sh | sh

# Alternative: Manual installation
# Download latest release
wget https://github.com/ollama/ollama/releases/download/v0.1.26/ollama-linux-amd64
chmod +x ollama-linux-amd64
sudo mv ollama-linux-amd64 /usr/local/bin/ollama

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

# Check status
sudo systemctl status ollama
```

#### Pull Required Models
```bash
# Wait for service to start
sleep 10

# Pull models (corrected for available models)
ollama pull nomic-embed-text      # Embedding model (274MB)
ollama pull gemma3:27b           # Generation model (17GB)
ollama pull qwen3:30b            # Multimodal model (18GB)

# Verify models are available
ollama list
```

### 5. Directory Structure and Permissions

#### Create Secure Directory Structure
```bash
# Create main directories
sudo mkdir -p /nvme0n1p2/{documents/{service,rnd,archive,quarantine},chroma_db,logs,backups,models,temp,config}

# Set ownership
sudo chown -R $USER:$USER /nvme0n1p2/

# Set permissions (Debian-compatible)
chmod 755 /nvme0n1p2/
chmod 755 /nvme0n1p2/documents/
chmod 755 /nvme0n1p2/documents/{service,rnd,archive}
chmod 750 /nvme0n1p2/documents/quarantine
chmod 755 /nvme0n1p2/chroma_db
chmod 700 /nvme0n1p2/logs
chmod 700 /nvme0n1p2/config
chmod 755 /nvme0n1p2/backups
chmod 755 /nvme0n1p2/models
chmod 755 /nvme0n1p2/temp

# Create security-specific subdirectories
mkdir -p /nvme0n1p2/logs
mkdir -p /nvme0n1p2/backups/{daily,weekly,monthly}
mkdir -p /nvme0n1p2/config/{users,certificates}

# Set restrictive permissions on security areas
chmod 700 /nvme0n1p2/logs
chmod 700 /nvme0n1p2/config/users
chmod 700 /nvme0n1p2/config/certificates
```

### 6. Nginx Configuration for Debian

#### Install and Configure Nginx
```bash
# Install nginx
sudo apt install -y nginx

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Create RAG system configuration
sudo tee /etc/nginx/sites-available/rag-system > /dev/null <<'EOF'
# Rate limiting configuration
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

server {
    listen 80;
    server_name localhost;  # Change to your domain
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-Robots-Tag "noindex, nofollow" always;
    
    # Hide nginx version
    server_tokens off;
    
    # Main API endpoints
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Authentication endpoints with stricter rate limiting
    location /auth/ {
        proxy_pass http://127.0.0.1:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Stricter rate limiting for auth
        limit_req zone=auth burst=5 nodelay;
    }
    
    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # Block access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ \.(env|config|json)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/rag-system /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Start nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 7. Systemd Service for RAG API

#### Create Systemd Service
```bash
# Create service user
sudo useradd -r -s /bin/false -m -d /var/lib/rag-system rag-system
sudo usermod -a -G ollama rag-system  # Add to ollama group for model access

# Create systemd service
sudo tee /etc/systemd/system/rag-api.service > /dev/null <<EOF
[Unit]
Description=Enhanced RAG System API
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=rag-system
Group=rag-system
WorkingDirectory=/nvme0n1p2
Environment=PATH=/nvme0n1p2/rag-env/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/nvme0n1p2/rag-env/bin/python production_api.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/nvme0n1p2

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

# Set permissions for service user
sudo chown -R rag-system:rag-system /nvme0n1p2
sudo chmod -R g+r /nvme0n1p2
sudo chmod -R g+w /nvme0n1p2/logs
sudo chmod -R g+w /nvme0n1p2/chroma_db
sudo chmod -R g+w /nvme0n1p2/backups
```

### 8. Security Configuration

#### Generate Secure Configuration
```bash
# Activate virtual environment
source /nvme0n1p2/rag-env/bin/activate

# Create secure configuration
python3.12 -c "
import secrets
import os
from pathlib import Path

# Create config directory
config_dir = Path('/nvme0n1p2/config')
config_dir.mkdir(exist_ok=True)

# Generate secure JWT secret
jwt_secret = secrets.token_urlsafe(64)

# Create .env file
env_content = f'''# RAG System Configuration for Debian
JWT_SECRET={jwt_secret}
API_HOST=0.0.0.0
API_PORT=8000

# Security settings
PASSWORD_MIN_LENGTH=12
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30

# Model configuration (Available Ollama models)
EMBEDDING_MODEL=nomic-embed-text
GENERATION_MODEL=gemma3:27b
MULTIMODAL_MODEL=qwen3:30b

# Debian-specific paths
OLLAMA_HOST=http://localhost:11434
'''

env_path = config_dir / '.env'
with open(env_path, 'w') as f:
    f.write(env_content)

# Set secure permissions
os.chmod(env_path, 0o600)

print(f'✅ Secure configuration created')
print(f'   JWT Secret: {len(jwt_secret)} characters')
print(f'   Config file: {env_path}')
print(f'   Permissions: {oct(os.stat(env_path).st_mode)[-3:]}')
"
```

### 9. Install and Test the RAG System

#### Download System Files
```bash
# Navigate to project directory
cd /nvme0n1p2

# Activate virtual environment
source rag-env/bin/activate

# Download/copy your Python files to /nvme0n1p2/
# config.py, security.py, production_api.py, etc.

# Test configuration
python validate_env.py

# Test model availability
python model_health.py
```

#### Initialize Security System
```bash
# Run security setup
python setup_security.py

# Validate security configuration
python validate_security.py

# Test user creation
python create_user.py
```

### 10. Start Services

#### Start RAG System Services
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Start and enable RAG API service
sudo systemctl enable rag-api
sudo systemctl start rag-api

# Check service status
sudo systemctl status rag-api

# Start nginx if not already running
sudo systemctl start nginx
sudo systemctl status nginx

# Check logs
sudo journalctl -u rag-api -f
sudo journalctl -u ollama -f
```

#### Test System
```bash
# Test health endpoint
curl http://localhost/health

# Test authentication (after creating admin user)
curl -X POST http://localhost/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=YOUR_ADMIN_PASSWORD"

# Test query endpoint
curl -X POST http://localhost/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Test query","include_sources":true}'
```

## Debian-Specific Considerations

### Package Management
```bash
# Update system regularly
sudo apt update && sudo apt upgrade -y

# Install security updates automatically
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Firewall Configuration (UFW)
```bash
# Install and configure firewall
sudo apt install -y ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (adjust port as needed)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow RAG API (if accessed directly)
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### Log Rotation
```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/rag-system > /dev/null <<'EOF'
/nvme0n1p2/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 rag-system rag-system
    postrotate
        /bin/systemctl reload rag-api
    endscript
}

/nvme0n1p2/logs/security.log {
    daily
    missingok
    rotate 365
    compress
    delaycompress
    notifempty
    create 600 rag-system rag-system
}
EOF
```

### Monitoring Setup
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Set up cron job for system monitoring
(crontab -l 2>/dev/null; echo "*/5 * * * * /nvme0n1p2/rag-env/bin/python /nvme0n1p2/monitor_processes.py") | crontab -
```

## Troubleshooting Debian-Specific Issues

### Python Issues
```bash
# If python3.12 is not available
sudo apt install -y python3-dev python3-venv python3-pip
python3 -m venv rag-env  # Use system python3
source rag-env/bin/activate
pip install --upgrade pip setuptools wheel

# Fix SSL issues
pip install --upgrade certifi
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R rag-system:rag-system /nvme0n1p2
sudo chmod -R 755 /nvme0n1p2
sudo chmod 700 /nvme0n1p2/config
sudo chmod 700 /nvme0n1p2/logs
```

### Service Issues
```bash
# Check service status
sudo systemctl status rag-api ollama nginx

# View logs
sudo journalctl -u rag-api --no-pager -l
sudo journalctl -u ollama --no-pager -l

# Restart services
sudo systemctl restart rag-api ollama nginx
```

### Network Issues
```bash
# Check port usage
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :11434
sudo netstat -tlnp | grep :80

# Test connectivity
curl -v http://localhost:11434/api/tags  # Ollama
curl -v http://localhost:8000/health     # RAG API
```

## Debian Package Versions

### Minimum Requirements
- **Debian 11+** or **Ubuntu 20.04+**
- **Python 3.10+** (3.12 recommended)
- **Nginx 1.18+**
- **OpenSSL 1.1.1+**
- **4GB RAM minimum** (16GB+ recommended)
- **20GB storage minimum** (100GB+ recommended)

### Performance Tuning for Debian
```bash
# Increase file limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize memory settings
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.conf

# Apply settings
sudo sysctl -p
```

This Debian-specific installation provides a production-ready deployment of the Enhanced RAG System with proper security, monitoring, and service management tailored for Debian-based systems.
