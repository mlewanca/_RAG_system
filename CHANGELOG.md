# Changelog

All notable changes to the RAG System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-08-26

### Added
- Streamlit-based web interface for user-friendly interaction
- Web-based login page with session management
- Visual document upload interface with drag-and-drop support
- Interactive query interface with expandable source citations
- Admin panel for user management through web UI
- Docker support for Streamlit deployment
- Web interface documentation (WEB_INTERFACE.md)
- Environment-based API URL configuration for containerized deployment

### Changed
- Enhanced user experience with visual web interface alongside API access
- Improved document upload workflow with immediate visual feedback

### Fixed
- None (new feature release)

## [0.1.0] - 2025-08-26

### Added
- Initial release of the RAG (Retrieval-Augmented Generation) System
- Document upload via API and Swagger UI interface
- ChromaDB vector storage integration for efficient document retrieval
- Ollama LLM integration with gemma3:27b and nomic-embed-text models
- JWT-based authentication system
- Role-based access control (admin, developer, service, hr, finance, legal, marketing roles)
- Multi-format document support (PDF, DOCX, XLSX, TXT, MD, PNG, JPG)
- Docker deployment configuration with docker-compose
- Safe mode configuration (docker-compose-safe.yml) for network isolation issues
- User management scripts for creating and managing users
- RESTful API with comprehensive Swagger/OpenAPI documentation
- Rate limiting per user role
- Document processing with metadata extraction
- Semantic search with source attribution
- Health check endpoints for monitoring

### Security
- Password strength validation
- Account lockout after failed login attempts
- Token-based authentication with expiration
- Role-based document access

### Tested
- Successfully processed and queried TNC640 technical documentation
- Verified document upload, processing, and retrieval functionality
- Tested with DMG parameter queries returning accurate results with source citations

### Known Issues
- Network configuration may conflict with system networks (use docker-compose-safe.yml)
- Grafana monitoring requires separate setup
- Swagger UI requires local assets download for offline environments

[0.1.0]: https://github.com/mlewanca/_RAG_system/releases/tag/v0.1