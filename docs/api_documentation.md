# RAG System API Documentation

## Overview

The RAG System provides a RESTful API for document retrieval and generation using advanced language models. All API endpoints require authentication except for the health check.

## Base URL

```
https://your-domain.com/api
```

For local development:
```
http://localhost:8000/api
```

## Authentication

The API uses JWT (JSON Web Token) authentication. To access protected endpoints, you must include a valid token in the Authorization header.

### Obtaining a Token

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
  "username": "your-username",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "TestPassword123!"}'
```

### Using the Token

Include the token in the Authorization header for all protected endpoints:

```
Authorization: Bearer <your-token>
```

## Endpoints

### 1. Health Check

Check if the API is running and healthy.

**Endpoint:** `GET /health`

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T15:30:00.000Z"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

### 2. Query Documents

Search and retrieve relevant documents with AI-generated responses.

**Endpoint:** `POST /api/query`

**Authentication:** Required

**Request Body:**
```json
{
  "query": "your search query",
  "max_results": 5,
  "filters": {
    "category": "service",
    "date_from": "2024-01-01"
  }
}
```

**Parameters:**
- `query` (required): The search query string
- `max_results` (optional): Maximum number of results to return (1-20, default: 5)
- `filters` (optional): Additional filters for document search

**Response:**
```json
{
  "query": "your search query",
  "results": [
    {
      "content": "AI-generated response based on retrieved documents",
      "metadata": {
        "type": "generated",
        "model": "gemma3:27b",
        "source_documents": 3
      },
      "score": 1.0,
      "generated_at": "2024-01-20T15:30:00.000Z"
    },
    {
      "content": "Document content excerpt...",
      "metadata": {
        "filename": "document.pdf",
        "source": "/path/to/document.pdf",
        "category": "service",
        "created_at": "2024-01-15T10:00:00.000Z"
      },
      "score": 0.95,
      "retrieved_at": "2024-01-20T15:30:00.000Z"
    }
  ],
  "timestamp": "2024-01-20T15:30:00.000Z",
  "processing_time": 1.234
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I configure the RAG system?",
    "max_results": 3
  }'
```

### 3. Upload Document (Admin Only)

Upload and process a new document into the system.

**Endpoint:** `POST /api/documents/upload`

**Authentication:** Required (Admin role only)

**Request Body:**
```json
{
  "file_path": "/path/to/document.pdf"
}
```

**Response:**
```json
{
  "filename": "document.pdf",
  "status": "success",
  "message": "Document processed successfully",
  "document_id": "d4f5g6h7i8j9k0"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/documents/new-guide.pdf"}'
```

### 4. User Profile

Get the current user's profile information.

**Endpoint:** `GET /api/user/profile`

**Authentication:** Required

**Response:**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "role": "developer",
  "full_name": "Test User",
  "created_at": "2024-01-01T00:00:00.000Z",
  "last_login": "2024-01-20T15:00:00.000Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/user/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Rate Limiting

API endpoints are rate-limited based on user roles:

| Role      | Requests per Minute |
|-----------|-------------------|
| service   | 5                 |
| developer | 15                |
| admin     | 50                |

When rate limit is exceeded, the API returns:
```json
{
  "detail": "Rate limit exceeded: 5 per 1 minute"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions for this operation"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Code Examples

### Python

```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "your-username"
PASSWORD = "your-password"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": USERNAME, "password": PASSWORD}
)
token = login_response.json()["access_token"]

# Headers with authentication
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Query documents
query_response = requests.post(
    f"{BASE_URL}/api/query",
    headers=headers,
    json={
        "query": "How to use the RAG system?",
        "max_results": 5
    }
)

results = query_response.json()
for result in results["results"]:
    print(f"Score: {result['score']}")
    print(f"Content: {result['content'][:200]}...")
    print("-" * 80)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function queryRAG() {
    try {
        // Login
        const loginResponse = await axios.post(`${BASE_URL}/api/auth/login`, {
            username: 'your-username',
            password: 'your-password'
        });
        
        const token = loginResponse.data.access_token;
        
        // Query documents
        const queryResponse = await axios.post(
            `${BASE_URL}/api/query`,
            {
                query: 'How to use the RAG system?',
                max_results: 5
            },
            {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('Results:', queryResponse.data.results);
        
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

queryRAG();
```

### cURL Examples

```bash
# Set variables
BASE_URL="http://localhost:8000"
USERNAME="your-username"
PASSWORD="your-password"

# Login and save token
TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" \
  | jq -r '.access_token')

# Query documents
curl -X POST "$BASE_URL/api/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "RAG system configuration",
    "max_results": 3,
    "filters": {
      "category": "service"
    }
  }' | jq '.'

# Get user profile
curl "$BASE_URL/api/user/profile" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

## WebSocket Support (Development)

For development environments, WebSocket connections are available at:

```
ws://localhost:8000/ws
```

## OpenAPI Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Best Practices

1. **Token Management**
   - Store tokens securely
   - Implement token refresh logic
   - Never expose tokens in URLs or logs

2. **Error Handling**
   - Always check response status codes
   - Implement retry logic for transient errors
   - Log errors appropriately

3. **Performance**
   - Use appropriate `max_results` values
   - Implement caching for frequent queries
   - Consider pagination for large result sets

4. **Security**
   - Always use HTTPS in production
   - Validate and sanitize all inputs
   - Keep authentication tokens short-lived