#!/bin/bash
# Enhanced RAG System - Environment Activation Script
# Activates the Python virtual environment and sets up the environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   echo "Please run as a regular user with sudo privileges"
   exit 1
fi

# Check if the virtual environment exists
if [ ! -d "/nvme0n1p2/rag-env" ]; then
    echo -e "${RED}❌ Virtual environment not found at /nvme0n1p2/rag-env${NC}"
    echo "Please run the setup script first:"
    echo "  curl -fsSL https://your-repo/debian_setup.sh | bash"
    exit 1
fi

# Check if the .env file exists
if [ ! -f "/nvme0n1p2/config/.env" ]; then
    echo -e "${YELLOW}⚠️  Configuration file not found at /nvme0n1p2/config/.env${NC}"
    echo "Creating a new configuration file..."
    # Create a new .env file with a secure JWT secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    cat > /nvme0n1p2/config/.env <<EOF
# RAG System Configuration - KEEP SECURE!
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
EMBEDDING_MODEL=nomic-embed-text
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
    chmod 600 /nvme0n1p2/config/.env
    echo -e "${GREEN}✅ Created new configuration file with secure JWT secret${NC}"
fi

# Check if the virtual environment is activated
if [ -f "/nvme0n1p2/rag-env/bin/activate" ]; then
    echo -e "${BLUE}🚀 Activating RAG System environment...${NC}"
    source /nvme0n1p2/rag-env/bin/activate
else
    echo -e "${RED}❌ Virtual environment activation script not found${NC}"
    exit 1
fi

# Check if the environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ Failed to activate virtual environment${NC}"
    exit 1
fi

# Check if the environment variables are loaded
if [ -f "/nvme0n1p2/config/.env" ]; then
    echo -e "${BLUE}🔐 Loading environment variables...${NC}"
    export $(grep -v '^#' /nvme0n1p2/config/.env | xargs)
fi

# Verify the activation
echo -e "${GREEN}✅ RAG System environment activated successfully${NC}"
echo "Virtual environment: $VIRTUAL_ENV"
echo "Python: $(which python)"
echo "Environment variables: $(env | grep -E 'JWT_SECRET|API_HOST|API_PORT|PASSWORD_MIN_LENGTH|MAX_LOGIN_ATTEMPTS|LOCKOUT_DURATION_MINUTES|EMBEDDING_MODEL|GENERATION_MODEL|MULTIMODAL_MODEL|OLLAMA_HOST|SYSTEMD_SERVICE_NAME|DEBUG|DEV_MODE')"
echo ""
echo "🚀 Next steps:"
echo "1. Run the security setup: python setup_security.py"
echo "2. Start the API server: python production_api.py"
echo "3. Access the system at: http://localhost/"
echo ""
echo -e "${BLUE}💡 Tip: Add 'source activate_rag.sh' to your .bashrc to activate the environment automatically${NC}"
