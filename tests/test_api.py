"""Tests for production API"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import json

@pytest.fixture
def api_client(test_config):
    """Create test API client"""
    with patch('src.production_api.RAGConfig', return_value=test_config):
        with patch('src.production_api.SecurityManager'):
            with patch('src.production_api.EnhancedRetriever'):
                with patch('src.production_api.DocumentProcessor'):
                    from src.production_api import app
                    return TestClient(app)

def test_health_check(api_client):
    """Test health check endpoint"""
    response = api_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_login_success(api_client):
    """Test successful login"""
    with patch('src.production_api.security_manager.authenticate_user') as mock_auth:
        mock_auth.return_value = {
            "username": "testuser",
            "role": "developer"
        }
        
        with patch('src.production_api.security_manager.create_access_token') as mock_token:
            mock_token.return_value = "test.jwt.token"
            
            response = api_client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "password123"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test.jwt.token"
            assert data["token_type"] == "bearer"

def test_login_failure(api_client):
    """Test failed login"""
    with patch('src.production_api.security_manager.authenticate_user') as mock_auth:
        mock_auth.return_value = None
        
        response = api_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

def test_query_endpoint_unauthorized(api_client):
    """Test query endpoint without authentication"""
    response = api_client.post(
        "/api/query",
        json={"query": "test query"}
    )
    
    assert response.status_code == 403  # Forbidden without auth header

def test_query_endpoint_authorized(api_client):
    """Test query endpoint with authentication"""
    with patch('src.production_api.security_manager.verify_token') as mock_verify:
        mock_verify.return_value = Mock(username="testuser", role="developer")
        
        with patch('src.production_api.retriever.query') as mock_query:
            mock_query.return_value = [
                {
                    "content": "Test result",
                    "metadata": {"source": "test.txt"},
                    "score": 0.95
                }
            ]
            
            response = api_client.post(
                "/api/query",
                json={"query": "test query", "max_results": 5},
                headers={"Authorization": "Bearer test.token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test query"
            assert len(data["results"]) == 1
            assert data["results"][0]["content"] == "Test result"

def test_document_upload_admin_only(api_client):
    """Test document upload requires admin role"""
    with patch('src.production_api.security_manager.verify_token') as mock_verify:
        # Test with non-admin user
        mock_verify.return_value = Mock(username="testuser", role="developer")
        
        response = api_client.post(
            "/api/documents/upload",
            json={"file_path": "/path/to/doc.pdf"},
            headers={"Authorization": "Bearer test.token"}
        )
        
        assert response.status_code == 403
        assert "Only administrators" in response.json()["detail"]

def test_document_upload_success(api_client):
    """Test successful document upload"""
    with patch('src.production_api.security_manager.verify_token') as mock_verify:
        mock_verify.return_value = Mock(username="admin", role="admin")
        
        with patch('src.production_api.document_processor.process_document') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "document_id": "doc123"
            }
            
            response = api_client.post(
                "/api/documents/upload",
                json={"file_path": "/path/to/doc.pdf"},
                headers={"Authorization": "Bearer test.token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["document_id"] == "doc123"

def test_user_profile(api_client):
    """Test user profile endpoint"""
    with patch('src.production_api.security_manager.verify_token') as mock_verify:
        mock_verify.return_value = Mock(username="testuser", role="developer")
        
        with patch('src.production_api.security_manager.get_user') as mock_get_user:
            mock_get_user.return_value = {
                "username": "testuser",
                "email": "test@example.com",
                "role": "developer",
                "full_name": "Test User",
                "created_at": "2024-01-01T00:00:00",
                "hashed_password": "should-be-removed"
            }
            
            response = api_client.get(
                "/api/user/profile",
                headers={"Authorization": "Bearer test.token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert "hashed_password" not in data

def test_rate_limiting(api_client):
    """Test rate limiting functionality"""
    with patch('src.production_api.security_manager.verify_token') as mock_verify:
        mock_verify.return_value = Mock(username="testuser", role="service")
        
        with patch('src.production_api.retriever.query') as mock_query:
            mock_query.return_value = []
            
            # Make multiple requests quickly
            for i in range(10):
                response = api_client.post(
                    "/api/query",
                    json={"query": f"test query {i}"},
                    headers={"Authorization": "Bearer test.token"}
                )
                
                # After 5 requests, should be rate limited
                if i >= 5:
                    assert response.status_code == 429  # Too Many Requests

def test_cors_headers(api_client):
    """Test CORS headers are properly set"""
    response = api_client.options("/api/query")
    
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers

def test_api_documentation(api_client):
    """Test API documentation endpoints"""
    # Test OpenAPI docs
    response = api_client.get("/api/docs")
    assert response.status_code == 200
    
    # Test ReDoc
    response = api_client.get("/api/redoc")
    assert response.status_code == 200