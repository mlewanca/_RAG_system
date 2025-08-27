"""Pytest configuration and fixtures"""

import pytest
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.security import SecurityManager
from src.document_processor import DocumentProcessor
from src.enhanced_retriever import EnhancedRetriever

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)

@pytest.fixture
def test_config(temp_dir):
    """Create test configuration"""
    class TestConfig(RAGConfig):
        base_dir: str = str(temp_dir)
        documents_dir: str = str(temp_dir / "documents")
        chroma_dir: str = str(temp_dir / "chroma_db")
        logs_dir: str = str(temp_dir / "logs")
        quarantine_dir: str = str(temp_dir / "quarantine")
        jwt_secret: str = "test-secret-key-for-testing-only-32chars"
        
        class Config:
            env_file = None
    
    config = TestConfig()
    
    # Create required directories
    for dir_attr in ['documents_dir', 'chroma_dir', 'logs_dir', 'quarantine_dir']:
        Path(getattr(config, dir_attr)).mkdir(parents=True, exist_ok=True)
    
    return config

@pytest.fixture
def security_manager(test_config):
    """Create test security manager"""
    return SecurityManager(test_config)

@pytest.fixture
def document_processor(test_config):
    """Create test document processor"""
    return DocumentProcessor(test_config)

@pytest.fixture
def retriever(test_config):
    """Create test retriever"""
    return EnhancedRetriever(test_config)

@pytest.fixture
def sample_user():
    """Create sample user data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "role": "developer",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }

@pytest.fixture
def sample_document(temp_dir):
    """Create a sample text document"""
    doc_path = temp_dir / "sample.txt"
    doc_path.write_text("""This is a sample document for testing.
It contains multiple paragraphs and sentences.

The document discusses RAG systems and their implementation.
This is useful for testing document processing and retrieval.""")
    return doc_path

@pytest.fixture
def auth_token(security_manager, sample_user):
    """Create an authentication token"""
    # Create user
    user_data = {
        "username": sample_user["username"],
        "email": sample_user["email"],
        "role": sample_user["role"],
        "full_name": sample_user["full_name"],
        "hashed_password": security_manager.get_password_hash(sample_user["password"]),
        "created_at": datetime.utcnow().isoformat(),
        "password_changed_at": datetime.utcnow().isoformat(),
        "disabled": False,
        "failed_attempts": 0,
        "locked_until": None
    }
    security_manager.save_user(sample_user["username"], user_data)
    
    # Create token
    token = security_manager.create_access_token(
        data={"sub": sample_user["username"], "role": sample_user["role"]}
    )
    return token

@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API responses"""
    def _mock_response(endpoint):
        if endpoint == "/api/tags":
            return {
                "models": [
                    {"name": "snowflake-arctic-embed2:latest", "size": 274230980},
                    {"name": "gemma3:27b", "size": 15955116544},
                ]
            }
        elif endpoint == "/api/embeddings":
            return {
                "embedding": [0.1] * 768  # Mock embedding vector
            }
        elif endpoint == "/api/generate":
            return {
                "response": "This is a mock response from the language model.",
                "done": True
            }
        return {}
    
    return _mock_response