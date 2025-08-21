# RAG System

This repository contains a Retrieval-Augmented Generation (RAG) system implementation with the following structure:

## Project Structure

```
.
├── config/                 # Configuration files
├── docs/                   # Documentation
├── scripts/                # Shell and Python scripts
├── logs/                   # Log files (automatically generated)
├── cache/                  # Cache files
├── chroma_db/              # Chroma vector database
├── documents/              # Document processing directories
├── monitoring/             # Monitoring tools
├── security/               # Security related components
└── test/                   # Test files
```

## Key Features

- Modular design with clear separation of concerns
- Comprehensive logging system organized by function (API, document processing, monitoring, security)
- Version control support via Git
- Debian-based deployment configuration

## Getting Started

1. Clone this repository
2. Set up your environment (see `docs/debian_installation_guide.md` for Debian-specific setup instructions)
3. Initialize the system using the provided scripts in `scripts/`

## Directory Structure Overview

- `config/`: Contains configuration files for the RAG system
- `docs/`: Documentation including installation guides and deployment instructions  
- `scripts/`: Automation scripts for setup and management
- `logs/`: Log output directory (will be populated during operation)
- `cache/`: Temporary cache files
- `chroma_db/`: Vector database storage
- `documents/`: Document processing workflow directories
- `monitoring/`: Monitoring tools and metrics
- `security/`: Security components and configurations

## Usage

The system is designed to be deployed on Debian-based systems. Refer to the documentation in `docs/` for detailed setup instructions.

## Contributing

This project uses Git for version control. Please follow standard Git practices for contributing changes.
