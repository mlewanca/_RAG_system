# Enhanced LangChain RAG System - Project Structure

## Directory Structure

```
/nvme0n1p2/                                    # Main base directory
├── documents/                                 # Document storage root
│   ├── service/                              # Service-level documents (755)
│   ├── rnd/                                  # R&D documents (755)
│   ├── archive/                              # Archived documents (755)
│   └── quarantine/                           # Failed processing files (750)
├── chroma_db/                                # Vector database storage (755)
├── logs/                                     # System logs (700 - RESTRICTED)
│   ├── security.log                         # Security event logs (700)
│   ├── api.log                              # API access logs
│   ├── document_processing.log              # Document processing logs
│   ├── monitoring.log                       # System monitoring logs
│   ├── user_creation.log                    # User creation events
│   ├── user_management.log                  # User management events
│   └── user_audit.log                       # User audit activities
├── backups/                                  # Backup storage (755)
│   ├── users/                               # User data backups (700)
│   ├── vector_db/                           # Vector DB backups
│   └── config/                              # Configuration backups (700)
├── config/                                   # Configuration files (700 - RESTRICTED)
│   ├── .env                                 # Environment variables (600)
│   ├── users.json                           # User database (600)
│   └── users_backup.json                   # User database backup (600)
└── scripts/                                 # Utility scripts (755)
```

## Core Application Files

### Configuration and Setup
- `config.py` - Main configuration with security settings
- `setup_security.py` - Automated security setup
- `validate_env.py` - Environment validation
- `validate_security.py` - Security configuration validation

### Document Processing
- `document_processor.py` - Enhanced document processor with multimodal support
- `batch_indexer.py` - Batch indexing with fault tolerance
- `enhanced_retriever.py` - Advanced retrieval with role-based filtering

### API and Security
- `production_api.py` - Main FastAPI application with security
- `security.py` - Enterprise-grade security and authentication

### User Management
- `create_user.py` - Interactive and batch user creation
- `bulk_user_import.py` - CSV-based bulk user import/export
- `user_management.py` - Comprehensive user administration
- `reset_password.py` - Password reset and management
- `user_audit.py` - User activity auditing and reporting

### Monitoring and Testing
- `monitor_processes.py` - System monitoring with security metrics
- `model_health.py` - Model availability and health checking
- `test_production.py` - Comprehensive test suite

## Setup Files

### Installation and Configuration
- `debian_setup.sh` - Automated installation script (executable)
- `requirements.txt` - Python dependencies
- `activate_rag.sh` - Environment activation helper (create manually)
- `configure_logrotate.txt` - Log rotation configuration
- `nginx_config.txt` - Nginx reverse proxy configuration

### Documentation Files
- `README.md` - Main system documentation
- `USER_MANAGEMENT.md` - User administration guide
- `USER_CREATION_GUIDE.md` - User creation procedures
- `BULK_USER_SETUP.md` - Bulk operations guide
- `USER_SECURITY_POLICIES.md` - Security policies and compliance

## Deployment Components

### System Integration
- `debian_service_manager.py` - Systemd service management
- `debian_config_py.py` - Debian-specific configuration
- `debian_installation_guide.md` - Detailed installation guide
- `deployment_guide.md` - Production deployment instructions

### Backup and Recovery
- `backup_strategy.txt` - Backup strategy documentation
- `validate_installation.txt` - Installation validation procedures

## Model Configuration
- `install_ollama.txt` - Ollama installation and model setup instructions

## Implementation Plan
- `updated_implementation_plan.md` - Current implementation plan
- `enhanced_rag_system_guide.markdown` - Detailed system guide

## Development Resources
- `complete_readme_md.md` - Complete system documentation
- `debian_requirements_txt.txt` - Debian-specific requirements
