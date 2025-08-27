# Development Environment Setup Guide

This guide will help you set up a development environment for the RAG system on Windows, macOS, or Linux.

## Prerequisites

- Python 3.9 or higher
- Git
- 8GB+ RAM recommended
- 20GB+ free disk space

## Platform-Specific Setup

### Windows Development

1. **Install Python**
   ```powershell
   # Using winget (Windows Package Manager)
   winget install Python.Python.3.11
   
   # Or download from python.org
   ```

2. **Install Git**
   ```powershell
   winget install Git.Git
   ```

3. **Install Ollama**
   - Download from: https://ollama.ai/download/windows
   - Run the installer
   - Verify installation:
   ```powershell
   ollama --version
   ```

### macOS Development

1. **Install Homebrew** (if not already installed)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python and Git**
   ```bash
   brew install python@3.11 git
   ```

3. **Install Ollama**
   ```bash
   brew install ollama
   ```

### Linux Development (Ubuntu/Debian)

1. **Update system and install dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv python3-pip git curl
   ```

2. **Install Ollama**
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

## Setting Up the Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/mlewanca/_RAG_system.git
cd _RAG_system
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r docs/requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Security
JWT_SECRET=your-secret-key-here-minimum-32-characters

# Paths (adjust for your system)
BASE_DIR=/path/to/your/data
DOCUMENTS_DIR=/path/to/your/data/documents
CHROMA_DIR=/path/to/your/data/chroma_db
LOGS_DIR=/path/to/your/data/logs

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000

# Model Configuration
EMBEDDING_MODEL=snowflake-arctic-embed2:latest
GENERATION_MODEL=gemma3:27b
MULTIMODAL_MODEL=qwen3:30b
```

### 5. Download Ollama Models

```bash
# Start Ollama service
ollama serve &

# Pull required models
ollama pull snowflake-arctic-embed2:latest
ollama pull gemma3:27b
ollama pull qwen3:30b
```

### 6. Initialize the System

```bash
# Create necessary directories
python scripts/setup_directories.py

# Initialize security
python src/setup_security.py

# Create your first user
python src/create_user.py
```

## Running the Development Server

### 1. Start Ollama (if not already running)

```bash
# Windows
ollama serve

# macOS/Linux (in background)
ollama serve &
```

### 2. Start the RAG API

```bash
# Development mode with auto-reload
uvicorn src.production_api:app --reload --host 127.0.0.1 --port 8000

# Or use the Python script directly
python src/production_api.py
```

### 3. Access the API

- API Documentation: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/health

## Development Tools

### Code Formatting

```bash
# Install formatting tools
pip install black isort

# Format code
black src/
isort src/
```

### Type Checking

```bash
# Install mypy
pip install mypy

# Run type checking
mypy src/
```

### Linting

```bash
# Install flake8
pip install flake8

# Run linting
flake8 src/ --max-line-length=100
```

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Testing API Endpoints

```bash
# Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your-username", "password": "your-password"}'

# Test query (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "max_results": 5}'
```

## Common Development Tasks

### Adding New Documents

```bash
# Single document
python src/document_processor.py --file /path/to/document.pdf

# Batch processing
python src/batch_indexer.py /path/to/documents --recursive
```

### Managing Users

```bash
# List users
python src/user_management.py list

# Create user
python src/create_user.py

# Disable user
python src/user_management.py disable username
```

### Monitoring Logs

```bash
# API logs
tail -f logs/api.log

# Security logs
tail -f logs/security.log

# All logs
tail -f logs/*.log
```

## IDE Configuration

### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- GitLens

Settings (`.vscode/settings.json`):
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.linting.mypyEnabled": true
}
```

### PyCharm

1. Set Python interpreter to virtual environment
2. Enable Black formatter
3. Configure mypy for type checking

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
killall ollama
ollama serve &
```

### Permission Errors

```bash
# Fix directory permissions
chmod -R 755 src/
chmod 600 .env
```

### Import Errors

```bash
# Ensure you're in the virtual environment
which python  # Should show venv path

# Reinstall dependencies
pip install -r docs/requirements.txt --force-reinstall
```

## Contributing

1. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and test
   ```bash
   pytest
   black src/
   mypy src/
   ```

3. Commit with meaningful messages
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

4. Push and create PR
   ```bash
   git push origin feature/your-feature-name
   ```

## Additional Resources

- [Project Documentation](../README.md)
- [API Documentation](http://localhost:8000/api/docs)
- [Deployment Guide](deployment_guide.md)
- [Security Policies](../security/README.md)