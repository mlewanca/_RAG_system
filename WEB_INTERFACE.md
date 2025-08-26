# RAG System Web Interface

The RAG System now includes a modern Streamlit-based web interface for easier interaction with the document management and query system.

## Features

### 🔐 Authentication
- Secure login page with JWT token management
- Session persistence across page refreshes
- Role-based access control (service, developer, admin)

### 📤 Document Upload
- Drag-and-drop file upload interface
- Support for multiple file formats:
  - PDF documents
  - Text files (.txt)
  - Word documents (.docx)
  - Excel files (.xlsx)
  - Images (PNG, JPG, JPEG)
  - Markdown files (.md)
- Automatic document categorization based on user role
- Admin users can specify document categories

### 🔍 Query Interface
- Intuitive text area for natural language queries
- Configurable number of results (1-10)
- AI-powered answers with source citations
- Expandable source documents with metadata
- Query history tracking (planned for future versions)

### 👨‍💼 Admin Panel
- User management: Create new users with specific roles
- Document management interface (coming soon)
- System statistics dashboard (coming soon)

## Access Points

- **Web Interface**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Direct API**: http://localhost:8000

## Docker Deployment

The web interface is automatically deployed as part of the Docker stack:

```bash
# Start all services including web interface
docker compose up -d

# View web interface logs
docker compose logs -f streamlit

# Rebuild web interface after changes
docker compose build streamlit
docker compose up -d streamlit
```

## Configuration

The web interface can be configured through environment variables:

- `API_BASE_URL`: Base URL for the RAG API (default: http://localhost:8000)

## Usage Guide

1. **Login**: Use your credentials to access the system
2. **Upload Documents**: Navigate to "Upload Document" to add new content
3. **Query Documents**: Use the "Query Documents" page to search your knowledge base
4. **Admin Tasks**: Admin users can manage users through the "Admin Panel"

## Security Notes

- All API calls require authentication
- Tokens are stored in the browser session
- Role-based access control enforces document visibility
- Admin functions are restricted to admin users only