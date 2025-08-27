#!/bin/bash

# Enhanced LangChain RAG System - Debian Setup Script
# Automated installation and configuration for Debian-based systems

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/tmp/rag-setup.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo -e "${BLUE}🚀 Enhanced RAG System - Debian Setup${NC}"
echo "=================================================="
echo "Log file: $LOG_FILE"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   echo "Please run as a regular user with sudo privileges"
   exit 1
fi

# Check OS compatibility
check_os() {
    echo -e "${BLUE}🐧 Checking OS compatibility...${NC}"
    
    if command -v lsb_release &> /dev/null; then
        OS=$(lsb_release -si)
        VERSION=$(lsb_release -sr)
        CODENAME=$(lsb_release -sc)
    elif [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
        CODENAME=$VERSION_CODENAME
    else
        echo -e "${RED}❌ Cannot determine OS version${NC}"
        exit 1
    fi
    
    echo "Detected: $OS $VERSION ($CODENAME)"
    
    case "$OS" in
        "Debian GNU/Linux"|"Debian")
            if [[ $(echo "$VERSION >= 11" | bc -l) -eq 1 ]]; then
                echo -e "${GREEN}✅ Debian $VERSION is supported${NC}"
            else
                echo -e "${YELLOW}⚠️  Debian $VERSION may have compatibility issues${NC}"
            fi
            ;;
        "Ubuntu")
            if [[ $(echo "$VERSION >= 20.04" | bc -l) -eq 1 ]]; then
                echo -e "${GREEN}✅ Ubuntu $VERSION is supported${NC}"
            else
                echo -e "${YELLOW}⚠️  Ubuntu $VERSION may have compatibility issues${NC}"
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  $OS is not officially supported but may work${NC}"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            ;;
    esac
}

# Update system packages
update_system() {
    echo -e "${BLUE}📦 Updating system packages...${NC}"
    
    sudo apt update
    sudo apt upgrade -y
    
    echo -e "${GREEN}✅ System updated${NC}"
}

# Install system dependencies
install_dependencies() {
    echo -e "${BLUE}📦 Installing system dependencies...${NC}"
    
    # Essential packages
    PACKAGES=(
        curl
        wget
        git
        nginx
        build-essential
        pkg-config
        libssl-dev
        libffi-dev
        libxml2-dev
        libxslt1-dev
        libjpeg-dev
        libpng-dev
        zlib1g-dev
        sqlite3
        libsqlite3-dev
        software-properties-common
        apt-transport-https
        ca-certificates
        gnupg
        lsb-release
        bc
        unzip
    )
    
    sudo apt install -y "${PACKAGES[@]}"
    
    echo -e "${GREEN}✅ System dependencies installed${NC}"
}

# Install Python 3.12
install_python() {
    echo -e "${BLUE}🐍 Installing Python 3.12...${NC}"
    
    # Check if Python 3.12 is already available
    if command -v python3.12 &> /dev/null; then
        echo -e "${GREEN}✅ Python 3.12 already installed${NC}"
        return
    fi
    
    # Try to install from repositories first
    if sudo apt install -y python3.12 python3.12-dev python3.12-venv python3.12-distutils &> /dev/null; then
        echo -e "${GREEN}✅ Python 3.12 installed from repositories${NC}"
    else
        echo -e "${YELLOW}⚠️  Python 3.12 not available in repositories${NC}"
        
        # For Ubuntu/derivatives, try deadsnakes PPA
        if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Mint"* ]]; then
            echo "Adding deadsnakes PPA..."
            sudo add-apt-repository ppa:deadsnakes/ppa -y
            sudo apt update
            sudo apt install -y python3.12 python3.12-dev python3.12-venv python3.12-distutils
            echo -e "${GREEN}✅ Python 3.12 installed from PPA${NC}"
        else
            echo -e "${YELLOW}⚠️  Using system Python 3${NC}"
            sudo apt install -y python3 python3-dev python3-venv python3-pip
        fi
    fi
    
    # Install pip for Python 3.12
    if ! python3.12 -m pip --version &> /dev/null; then
        echo "Installing pip for Python 3.12..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
    fi
    
    # Verify installation
    python3.12 --version
    echo -e "${GREEN}✅ Python setup complete${NC}"
}

# Create directory structure
create_directories() {
    echo -e "${BLUE}📁 Creating directory structure...${NC}"
    
    # Create main directories
    sudo mkdir -p /nvme0n1p2/{documents/{service,rnd,archive,quarantine},chroma_db,logs,backups,models,temp,config}
    
    # Set ownership
    sudo chown -R $USER:$USER /nvme0n1p2/
    
    # Set permissions
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
    
    # Create subdirectories
    mkdir -p /nvme0n1p2/logs/{security,api,document_processing,monitoring}
    mkdir -p /nvme0n1p2/backups/{daily,weekly,monthly}
    mkdir -p /nvme0n1p2/config/{users,certificates}
    
    # Set restrictive permissions on security areas
    chmod 700 /nvme0n1p2/logs/security
    chmod 700 /nvme0n1p2/config/users
    chmod 700 /nvme0n1p2/config/certificates
    
    echo -e "${GREEN}✅ Directory structure created${NC}"
}

# Create Python virtual environment
create_venv() {
    echo -e "${BLUE}🐍 Creating Python virtual environment...${NC}"
    
    cd /nvme0n1p2
    
    # Determine Python command
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    else
        PYTHON_CMD="python3"
    fi
    
    # Create virtual environment
    $PYTHON_CMD -m venv rag-env
    
    # Activate and upgrade pip
    source rag-env/bin/activate
    pip install --upgrade pip setuptools wheel
    
    echo -e "${GREEN}✅ Virtual environment created${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    
    cd /nvme0n1p2
    source rag-env/bin/activate
    
    # Core dependencies
    echo "Installing core dependencies..."
    pip install --upgrade \
        langchain==0.3 \
        langchain-community \
        langchain-ollama \
        pypdf \
        "unstructured[pdf]" \
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
    
    # Security dependencies
    echo "Installing security dependencies..."
    pip install --upgrade \
        "passlib[bcrypt]" \
        "python-jose[cryptography]" \
        python-multipart \
        cryptography \
        bcrypt \
        pyjwt \
        email-validator \
        slowapi
    
    # Debian-specific packages
    echo "Installing Debian-specific packages..."
    pip install --upgrade \
        distro
    
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

# Install Ollama
install_ollama() {
    echo -e "${BLUE}🤖 Installing Ollama...${NC}"
    
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Create systemd service if it doesn't exist
    if [ ! -f /etc/systemd/system/ollama.service ]; then
        echo "Creating Ollama systemd service..."
        
        # Create ollama user
        sudo useradd -r -s /bin/false -m -d /var/lib/ollama ollama || true
        
        # Create service file
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
    fi
    
    # Start and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable ollama
    sudo systemctl start ollama
    
    # Wait for service to start
    echo "Waiting for Ollama service to start..."
    sleep 10
    
    # Check if service is running
    if sudo systemctl is-active --quiet ollama; then
        echo -e "${GREEN}✅ Ollama service is running${NC}"
    else
        echo -e "${RED}❌ Ollama service failed to start${NC}"
        sudo systemctl status ollama
        exit 1
    fi
}

# Pull Ollama models
pull_models() {
    echo -e "${BLUE}🤖 Pulling Ollama models...${NC}"
    
    # Wait for Ollama to be ready
    echo "Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags &> /dev/null; then
            break
        fi
        sleep 2
    done
    
    # Pull required models
    MODELS=(
        "snowflake-arctic-embed2:latest"
        "gemma3:27b"
        "qwen3:30b"
    )
    
    for model in "${MODELS[@]}"; do
        echo "Pulling $model..."
        ollama pull "$model"
    done
    
    # Verify models
    echo "Verifying models..."
    ollama list
    
    echo -e "${GREEN}✅ Models pulled successfully${NC}"
}

# Create secure configuration
create_config() {
    echo -e "${BLUE}🔐 Creating secure configuration...${NC}"
    
    cd /nvme0n1p2
    source rag-env/bin/activate
    
    # Generate secure JWT secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    
    # Create .env file
    cat > config/.env <<EOF
# RAG System Configuration for Debian - KEEP SECURE!
# Generated on $(date)
JWT_SECRET=$JWT_SECRET

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security Settings
PASSWORD_MIN_LENGTH=12
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30

# Model Configuration (Available Ollama Models)
EMBEDDING_MODEL=snowflake-arctic-embed2:latest
GENERATION_MODEL=gemma3:27b
MULTIMODAL_MODEL=qwen3:30b

# Debian-specific Configuration
OLLAMA_HOST=http://localhost:11434
SYSTEMD_SERVICE_NAME=rag-api

# Development Settings (set to false in production)
DEBUG=false
DEV_MODE=false
EOF
    
    # Set secure permissions
    chmod 600 config/.env
    
    echo -e "${GREEN}✅ Secure configuration created${NC}"
    echo "JWT Secret: ${#JWT_SECRET} characters"
}

# Configure Nginx
configure_nginx() {
    echo -e "${BLUE}🌐 Configuring Nginx...${NC}"
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Create RAG system configuration
    sudo tee /etc/nginx/sites-available/rag-system > /dev/null <<'EOF'
# Rate limiting configuration
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

server {
    listen 80;
    server_name localhost;
    
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
    sudo ln -sf /etc/nginx/sites-available/rag-system /etc/nginx/sites-enabled/
    
    # Test configuration
    sudo nginx -t
    
    # Start nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
    
    echo -e "${GREEN}✅ Nginx configured${NC}"
}

# Create systemd service for RAG API
create_systemd_service() {
    echo -e "${BLUE}🔧 Creating systemd service...${NC}"
    
    # Create service user
    sudo useradd -r -s /bin/false -m -d /var/lib/rag-system rag-system || true
    sudo usermod -a -G ollama rag-system
    
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
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    echo -e "${GREEN}✅ Systemd service created${NC}"
}

# Configure firewall
configure_firewall() {
    echo -e "${BLUE}🔥 Configuring firewall...${NC}"
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        # Configure UFW
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        
        # Allow SSH
        sudo ufw allow 22/tcp
        
        # Allow HTTP/HTTPS
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        
        # Ask about enabling firewall
        read -p "Enable firewall? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ufw --force enable
            echo -e "${GREEN}✅ Firewall enabled${NC}"
        else
            echo -e "${YELLOW}⚠️  Firewall not enabled${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  UFW not available, skipping firewall configuration${NC}"
    fi
}

# Configure log rotation
configure_log_rotation() {
    echo -e "${BLUE}📋 Configuring log rotation...${NC}"
    
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

/nvme0n1p2/logs/security/*.log {
    daily
    missingok
    rotate 365
    compress
    delaycompress
    notifempty
    create 600 rag-system rag-system
}
EOF
    
    echo -e "${GREEN}✅ Log rotation configured${NC}"
}

# Final system test
test_installation() {
    echo -e "${BLUE}🧪 Testing installation...${NC}"
    
    cd /nvme0n1p2
    source rag-env/bin/activate
    
    # Test Python imports
    echo "Testing Python imports..."
    python3 -c "
import langchain
import fastapi
import ollama
import chromadb
import passlib
print('✅ All Python imports successful')
"
    
    # Test Ollama
    echo "Testing Ollama connection..."
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo -e "${GREEN}✅ Ollama is accessible${NC}"
    else
        echo -e "${RED}❌ Ollama is not accessible${NC}"
    fi
    
    # Test Nginx
    echo "Testing Nginx..."
    if sudo systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx is running${NC}"
    else
        echo -e "${RED}❌ Nginx is not running${NC}"
    fi
    
    # Test directory permissions
    echo "Testing directory permissions..."
    if [ "$(stat -c %a /nvme0n1p2/config/.env)" = "600" ]; then
        echo -e "${GREEN}✅ Secure file permissions${NC}"
    else
        echo -e "${YELLOW}⚠️  File permissions may need adjustment${NC}"
    fi
    
    echo -e "${GREEN}✅ Installation test complete${NC}"
}

# Print completion message
print_completion() {
    echo ""
    echo -e "${GREEN}🎉 RAG System installation complete!${NC}"
    echo "=================================================="
    echo ""
    echo "📁 Installation directory: /nvme0n1p2"
    echo "🐍 Virtual environment: /nvme0n1p2/rag-env"
    echo "🔐 Configuration: /nvme0n1p2/config/.env"
    echo "📋 Logs: /nvme0n1p2/logs/"
    echo ""
    echo "🚀 Next steps:"
    echo "1. Copy your RAG system Python files to /nvme0n1p2/"
    echo "2. Activate the virtual environment:"
    echo "   cd /nvme0n1p2 && source rag-env/bin/activate"
    echo "3. Run setup_security.py to initialize user management"
    echo "4. Start the RAG API service:"
    echo "   sudo systemctl start rag-api"
    echo "5. Check service status:"
    echo "   sudo systemctl status rag-api"
    echo ""
    echo "🌐 Access the system at: http://localhost/"
    echo "📊 Health check: http://localhost/health"
    echo ""
    echo "📖 Documentation: See README.md for complete usage instructions"
    echo ""
    echo -e "${BLUE}Log file saved to: $LOG_FILE${NC}"
}

# Main installation flow
main() {
    echo "Starting Enhanced RAG System installation for Debian..."
    echo ""
    
    check_os
    update_system
    install_dependencies
    install_python
    create_directories
    create_venv
    install_python_deps
    install_ollama
    pull_models
    create_config
    configure_nginx
    create_systemd_service
    configure_firewall
    configure_log_rotation
    test_installation
    print_completion
}

# Error handling
trap 'echo -e "${RED}❌ Installation failed. Check $LOG_FILE for details.${NC}"; exit 1' ERR

# Run main installation
main "$@"