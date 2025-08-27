#!/bin/bash
#
# RAG System Quick Install Script
# This script provides a one-command installation of the RAG system using Docker
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/mlewanca/_RAG_system.git"
INSTALL_DIR="$HOME/rag-system"
ADMIN_PASSWORD=$(openssl rand -base64 12)

# Functions
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║       RAG System Quick Install Script        ║"
    echo "║         Debian/Ubuntu Installation           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check OS
    if [[ ! -f /etc/debian_version ]]; then
        echo -e "${RED}Error: This script is for Debian/Ubuntu systems only.${NC}"
        exit 1
    fi
    
    # Check memory
    MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
    if [[ $MEM_TOTAL -lt 7500 ]]; then
        echo -e "${YELLOW}Warning: System has less than 8GB RAM. Performance may be affected.${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check disk space
    DISK_AVAILABLE=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $DISK_AVAILABLE -lt 40 ]]; then
        echo -e "${YELLOW}Warning: Less than 40GB disk space available.${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Prerequisites check passed${NC}"
}

install_docker() {
    echo -e "${YELLOW}Installing Docker...${NC}"
    
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker already installed${NC}"
    else
        # Install Docker
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        echo -e "${GREEN}✓ Docker installed${NC}"
        echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"
    fi
    
    # Install Docker Compose plugin
    if docker compose version &> /dev/null; then
        echo -e "${GREEN}✓ Docker Compose already installed${NC}"
    else
        echo -e "${YELLOW}Installing Docker Compose plugin...${NC}"
        sudo apt update
        sudo apt install -y docker-compose-plugin
        echo -e "${GREEN}✓ Docker Compose installed${NC}"
    fi
}

clone_repository() {
    echo -e "${YELLOW}Cloning RAG system repository...${NC}"
    
    if [[ -d "$INSTALL_DIR" ]]; then
        echo -e "${YELLOW}Installation directory already exists.${NC}"
        read -p "Remove existing installation? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
    fi
    
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    echo -e "${GREEN}✓ Repository cloned${NC}"
}

configure_environment() {
    echo -e "${YELLOW}Configuring environment...${NC}"
    
    # Create .env file
    cp .env.example .env
    
    # Generate secure JWT secret
    JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')
    # Use | as delimiter since JWT secret might contain / characters
    sed -i "s|your-secret-key-here-minimum-32-characters-long|$JWT_SECRET|" .env
    
    # Create data directories
    mkdir -p data/{config,logs,documents,chroma_db,backups,cache}
    
    echo -e "${GREEN}✓ Environment configured${NC}"
}

start_services() {
    echo -e "${YELLOW}Starting services...${NC}"
    
    # Start services
    docker compose up -d
    
    # Wait for services to be ready
    echo -e "${YELLOW}Waiting for services to start...${NC}"
    sleep 30
    
    # Check if services are running
    if docker compose ps | grep -q "rag-api.*running"; then
        echo -e "${GREEN}✓ Services started successfully${NC}"
    else
        echo -e "${RED}Error: Services failed to start${NC}"
        docker compose logs
        exit 1
    fi
}

pull_models() {
    echo -e "${YELLOW}Pulling AI models (this may take a while)...${NC}"
    
    # Pull embedding model
    echo -e "${YELLOW}Pulling embedding model...${NC}"
    docker compose exec -T ollama ollama pull snowflake-arctic-embed2:latest
    
    # Pull generation model
    echo -e "${YELLOW}Pulling generation model (large download)...${NC}"
    docker compose exec -T ollama ollama pull gemma3:27b
    
    echo -e "${GREEN}✓ AI models downloaded${NC}"
}

create_admin_user() {
    echo -e "${YELLOW}Creating admin user...${NC}"
    
    # Create admin user
    docker compose exec -T rag-api python src/create_user.py --batch \
        --username admin \
        --email admin@localhost \
        --role admin \
        --password "$ADMIN_PASSWORD" \
        --full-name "System Administrator"
    
    echo -e "${GREEN}✓ Admin user created${NC}"
}

test_installation() {
    echo -e "${YELLOW}Testing installation...${NC}"
    
    # Test health endpoint
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e "${GREEN}✓ API health check passed${NC}"
    else
        echo -e "${RED}Error: API health check failed${NC}"
        return 1
    fi
    
    # Test authentication
    TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}" \
        | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [[ -n "$TOKEN" ]]; then
        echo -e "${GREEN}✓ Authentication test passed${NC}"
    else
        echo -e "${RED}Error: Authentication test failed${NC}"
        return 1
    fi
    
    return 0
}

print_success() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║          RAG System Installation Complete!               ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
    echo -e "${BLUE}Access Information:${NC}"
    echo "─────────────────────────────────────────────────────────"
    echo -e "API URL:        ${GREEN}http://localhost:8000${NC}"
    echo -e "API Docs:       ${GREEN}http://localhost:8000/api/docs${NC}"
    echo -e "Username:       ${GREEN}admin${NC}"
    echo -e "Password:       ${GREEN}$ADMIN_PASSWORD${NC}"
    echo
    echo -e "${BLUE}Installation Directory:${NC} $INSTALL_DIR"
    echo
    echo -e "${YELLOW}⚠️  IMPORTANT: Please save the admin password above!${NC}"
    echo -e "${YELLOW}⚠️  Change it after first login for security.${NC}"
    echo
    echo -e "${BLUE}Quick Commands:${NC}"
    echo "─────────────────────────────────────────────────────────"
    echo "View logs:      cd $INSTALL_DIR && docker compose logs -f"
    echo "Stop services:  cd $INSTALL_DIR && docker compose down"
    echo "Start services: cd $INSTALL_DIR && docker compose up -d"
    echo
    echo -e "${GREEN}Thank you for installing the RAG System!${NC}"
}

cleanup_on_error() {
    echo -e "${RED}Installation failed. Cleaning up...${NC}"
    cd "$HOME"
    docker compose -f "$INSTALL_DIR/docker-compose.yml" down -v 2>/dev/null || true
    echo -e "${YELLOW}Partial installation cleaned up.${NC}"
}

# Main installation flow
main() {
    print_banner
    
    # Set trap for cleanup on error
    trap cleanup_on_error ERR
    
    # Run installation steps
    check_prerequisites
    install_docker
    clone_repository
    configure_environment
    start_services
    pull_models
    create_admin_user
    
    # Test installation
    if test_installation; then
        print_success
    else
        echo -e "${RED}Installation completed but tests failed.${NC}"
        echo -e "${YELLOW}Check the logs: cd $INSTALL_DIR && docker compose logs${NC}"
        exit 1
    fi
    
    # Remove trap
    trap - ERR
}

# Run main function
main

# Save credentials to file
echo "Admin Password: $ADMIN_PASSWORD" > "$INSTALL_DIR/admin_credentials.txt"
chmod 600 "$INSTALL_DIR/admin_credentials.txt"