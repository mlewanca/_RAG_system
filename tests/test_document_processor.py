"""Tests for document processor module"""

import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch

def test_file_hash_calculation(document_processor, sample_document):
    """Test file hash calculation"""
    hash1 = document_processor.get_file_hash(sample_document)
    hash2 = document_processor.get_file_hash(sample_document)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 character hex string

def test_metadata_extraction(document_processor, sample_document):
    """Test metadata extraction from files"""
    metadata = document_processor.extract_metadata(sample_document)
    
    assert metadata["filename"] == "sample.txt"
    assert metadata["file_path"] == str(sample_document)
    assert metadata["file_size"] > 0
    assert metadata["mime_type"] == "text/plain"
    assert "created_at" in metadata
    assert "modified_at" in metadata
    assert "processed_at" in metadata
    assert "file_hash" in metadata

def test_duplicate_detection(document_processor, sample_document):
    """Test duplicate document detection"""
    # Mock the ChromaDB client
    with patch.object(document_processor.client, 'get_or_create_collection') as mock_collection:
        # First check - no duplicate
        mock_collection.return_value.get.return_value = {'ids': []}
        assert not document_processor.is_duplicate("test_hash")
        
        # Second check - duplicate exists
        mock_collection.return_value.get.return_value = {'ids': ['existing_id']}
        assert document_processor.is_duplicate("test_hash")

def test_document_loading(document_processor, sample_document):
    """Test document loading"""
    documents = document_processor.load_document(sample_document)
    
    assert documents is not None
    assert len(documents) > 0
    assert hasattr(documents[0], 'page_content')

def test_unsupported_file_type(document_processor, temp_dir):
    """Test handling of unsupported file types"""
    unsupported_file = temp_dir / "test.xyz"
    unsupported_file.write_text("content")
    
    documents = document_processor.load_document(unsupported_file)
    assert documents is None

@patch('src.document_processor.OllamaEmbeddings')
@patch('chromadb.PersistentClient')
def test_document_processing(mock_chroma, mock_embeddings, document_processor, sample_document):
    """Test complete document processing"""
    # Setup mocks
    mock_collection = Mock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    mock_collection.get.return_value = {'ids': []}  # No duplicates
    mock_collection.count.return_value = 0
    
    mock_embeddings.return_value.embed_documents.return_value = [[0.1] * 768]  # Mock embeddings
    
    # Process document
    result = document_processor.process_document(str(sample_document))
    
    assert result["status"] == "success"
    assert "document_id" in result
    assert "chunks" in result
    assert result["chunks"] > 0

def test_document_quarantine_on_error(document_processor, temp_dir):
    """Test document quarantine on processing error"""
    # Create a file that will cause an error
    error_file = temp_dir / "error.txt"
    error_file.write_text("content")
    
    # Mock an error during processing
    with patch.object(document_processor, 'load_document', side_effect=Exception("Test error")):
        result = document_processor.process_document(str(error_file))
    
    assert result["status"] == "error"
    assert result["quarantined"] == True
    
    # Check file was moved to quarantine
    quarantine_path = document_processor.quarantine_dir / error_file.name
    assert quarantine_path.exists()

def test_batch_processing(document_processor, temp_dir):
    """Test batch document processing"""
    # Create multiple test files
    files = []
    for i in range(3):
        file_path = temp_dir / f"test_{i}.txt"
        file_path.write_text(f"Test content {i}")
        files.append(str(file_path))
    
    # Mock the process_document method
    with patch.object(document_processor, 'process_document') as mock_process:
        mock_process.return_value = {"status": "success", "chunks": 1}
        
        results = document_processor.batch_process(files, max_workers=2)
        
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        assert mock_process.call_count == 3

def test_statistics_gathering(document_processor):
    """Test document statistics gathering"""
    # Mock ChromaDB collection
    with patch.object(document_processor.client, 'get_or_create_collection') as mock_collection:
        mock_collection.return_value.count.return_value = 100
        mock_collection.return_value.get.return_value = {
            'metadatas': [
                {'mime_type': 'text/plain', 'file_hash': 'hash1'},
                {'mime_type': 'text/plain', 'file_hash': 'hash2'},
                {'mime_type': 'application/pdf', 'file_hash': 'hash3'},
            ]
        }
        
        stats = document_processor.get_statistics()
        
        assert stats["total_chunks"] == 100
        assert stats["unique_documents"] == 3
        assert stats["document_types"]["text/plain"] == 2
        assert stats["document_types"]["application/pdf"] == 1

def test_text_splitting(document_processor):
    """Test text splitting functionality"""
    from langchain.schema import Document
    
    # Create a long document
    long_text = "This is a test. " * 100
    doc = Document(page_content=long_text)
    
    chunks = document_processor.text_splitter.split_documents([doc])
    
    assert len(chunks) > 1
    assert all(len(chunk.page_content) <= 1000 for chunk in chunks)