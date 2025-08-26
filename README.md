# RAG System

[![Version](https://img.shields.io/badge/version-0.1-blue.svg)](https://github.com/mlewanca/_RAG_system/releases/tag/v0.1)

A production-ready Retrieval-Augmented Generation (RAG) system with enterprise-grade security, scalability, and modularity.

## 🚀 Quick Start

```bash
# One-line installation
curl -fsSL https://raw.githubusercontent.com/mlewanca/_RAG_system/master/scripts/quick_install.sh | bash
```

Or see the [Quick Install Guide](docs/quick_install.md) for more options.

> **Note**: The system now uses external Ollama by default. See [External Ollama Setup](docs/external_ollama_setup.md) for configuration details.

## 📋 Project Overview

This RAG system provides:
- **Secure Document Management**: Role-based access control with fine-grained permissions
- **AI-Powered Search**: Advanced retrieval using Ollama models
- **Enterprise Security**: JWT authentication, rate limiting, and audit logging
- **Easy Scalability**: Modular design for adding new departments and roles
- **Production Ready**: Docker support, monitoring, and comprehensive documentation

## 🏗️ Project Structure

```
.
├── src/                    # Core application code
├── config/                 # Configuration files
├── docs/                   # Documentation
├── scripts/                # Setup and management scripts
├── tests/                  # Test suite
├── examples/               # Example implementations
├── nginx/                  # Nginx configuration
├── .github/workflows/      # CI/CD pipelines
└── docker-compose.yml      # Docker orchestration
```

## ✨ Key Features

- **Modular Architecture**: Easy to extend with new user groups and document categories
- **Multi-Model Support**: Gemma3:27b, Qwen3:30b, and Nomic embeddings
- **Role-Based Access**: Flexible permission system for different departments
- **RESTful API**: Well-documented API with FastAPI
- **Docker Support**: Easy deployment with Docker Compose
- **Comprehensive Monitoring**: Prometheus, Grafana, and structured logging
- **Security First**: Enterprise-grade authentication and authorization

## 📚 Documentation

- **Installation**:
  - [Quick Install Guide](docs/quick_install.md) - Get started in 5 minutes
  - [Debian Installation Guide](docs/debian_installation_guide.md) - Comprehensive setup
  - [Development Setup](docs/development_setup.md) - For developers
  - [External Ollama Setup](docs/external_ollama_setup.md) - Using external Ollama
  - [Port Configuration](docs/port_configuration.md) - Network ports and access

- **Usage**:
  - [API Documentation](docs/api_documentation.md) - Complete API reference
  - [Adding User Groups](docs/adding_user_groups.md) - Extend with new roles
  - [RAG & Ollama Architecture](docs/rag_ollama_architecture.md) - How RAG works with models
  - [Deployment Guide](docs/deployment_guide.md) - Production deployment

## 🛠️ Installation Methods

### Docker (Recommended)
```bash
git clone https://github.com/mlewanca/_RAG_system.git
cd _RAG_system
cp .env.example .env
docker compose up -d
```

### Native Installation
See the [Debian Installation Guide](docs/debian_installation_guide.md) for detailed instructions.

## 🔧 Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:
   - Set secure JWT_SECRET
   - Configure paths and ports
   - Adjust model settings

3. Create your first admin user:
   ```bash
   docker compose exec rag-api python src/create_user.py
   ```

## 🚦 Usage Examples

> **Note**: If accessing through nginx, use port 8880 for HTTP or 8843 for HTTPS (e.g., `http://localhost:8880/api`). Direct API access remains on port 8000.

### Basic Query
```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r .access_token)

# Query documents
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"How to configure the system?","max_results":5}'
```

### Python Client
```python
from examples.api_client import RAGClient

client = RAGClient("http://localhost:8000")
client.login("admin", "your-password")
results = client.query("system configuration")
```

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Fine-grained permissions per department
- **Rate Limiting**: Configurable limits per role
- **Audit Logging**: Comprehensive activity tracking
- **Password Policies**: Enforced complexity requirements
- **Account Lockout**: Protection against brute force

## 📊 Monitoring

- **Nginx (HTTP)**: http://localhost:8880
- **Nginx (HTTPS)**: https://localhost:8843
- **API (Direct)**: http://localhost:8000
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000
- **Health Check**: http://localhost:8000/health or http://localhost:8880/health
- **Structured Logging**: JSON format for easy parsing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/) and [Ollama](https://ollama.ai/)
- Uses [ChromaDB](https://www.trychroma.com/) for vector storage
- API powered by [FastAPI](https://fastapi.tiangolo.com/)

## 📞 Support

- **Documentation**: See `/docs` folder
- **Issues**: [GitHub Issues](https://github.com/mlewanca/_RAG_system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mlewanca/_RAG_system/discussions)

---

Made with ❤️ by the RAG System Team
