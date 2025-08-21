"""Tests for enhanced retriever module"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

@pytest.mark.asyncio
async def test_role_based_filters(retriever):
    """Test role-based document filtering"""
    # Test admin role - should access all categories
    filters = retriever.get_user_filters("admin")
    assert "$or" in filters
    assert len(filters["$or"]) == 3
    
    # Test developer role
    filters = retriever.get_user_filters("developer")
    assert len(filters["$or"]) == 2
    
    # Test service role
    filters = retriever.get_user_filters("service")
    assert len(filters["$or"]) == 1
    assert filters["$or"][0]["category"] == "service"

@pytest.mark.asyncio
async def test_query_with_no_results(retriever):
    """Test query when no documents match"""
    with patch.object(retriever.client, 'get_or_create_collection') as mock_collection:
        mock_collection.return_value.query.return_value = {
            'ids': [[]],
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }
        
        results = await retriever.query("test query")
        
        assert len(results) == 1
        assert "No relevant documents found" in results[0]["content"]

@pytest.mark.asyncio
async def test_query_with_results(retriever):
    """Test successful query with results"""
    with patch.object(retriever.client, 'get_or_create_collection') as mock_collection:
        with patch.object(retriever.embeddings, 'embed_query') as mock_embed:
            with patch.object(retriever, '_generate_response') as mock_generate:
                # Setup mocks
                mock_embed.return_value = [0.1] * 768
                mock_collection.return_value.count.return_value = 10
                mock_collection.return_value.query.return_value = {
                    'ids': [['doc1', 'doc2']],
                    'documents': [['Document 1 content', 'Document 2 content']],
                    'metadatas': [[
                        {'source': 'file1.txt', 'category': 'service'},
                        {'source': 'file2.txt', 'category': 'service'}
                    ]],
                    'distances': [[0.1, 0.2]]
                }
                mock_generate.return_value = "Generated response based on documents"
                
                results = await retriever.query("test query", max_results=5, user_role="developer")
                
                assert len(results) == 3  # Generated + 2 documents
                assert results[0]["content"] == "Generated response based on documents"
                assert results[0]["metadata"]["type"] == "generated"
                assert results[1]["content"] == "Document 1 content"
                assert results[2]["content"] == "Document 2 content"

@pytest.mark.asyncio
async def test_query_with_custom_filters(retriever):
    """Test query with custom filters"""
    with patch.object(retriever.client, 'get_or_create_collection') as mock_collection:
        with patch.object(retriever.embeddings, 'embed_query') as mock_embed:
            mock_embed.return_value = [0.1] * 768
            mock_collection.return_value.count.return_value = 10
            
            custom_filters = {"file_type": "pdf"}
            await retriever.query("test query", filters=custom_filters)
            
            # Verify filters were combined
            call_args = mock_collection.return_value.query.call_args
            where_clause = call_args.kwargs.get('where')
            assert "$and" in where_clause

@pytest.mark.asyncio
async def test_search_similar_documents(retriever):
    """Test similar document search"""
    with patch.object(retriever.client, 'get_or_create_collection') as mock_collection:
        # Mock getting the source document
        mock_collection.return_value.get.return_value = {
            'ids': ['doc1'],
            'embeddings': [[0.1] * 768],
            'metadatas': [{'source': 'original.txt'}],
            'documents': ['Original content']
        }
        
        # Mock similarity search
        mock_collection.return_value.query.return_value = {
            'ids': [['doc1', 'doc2', 'doc3']],
            'documents': [['Original content', 'Similar doc 1', 'Similar doc 2']],
            'metadatas': [[
                {'source': 'original.txt'},
                {'source': 'similar1.txt'},
                {'source': 'similar2.txt'}
            ]],
            'distances': [[0.0, 0.1, 0.2]]
        }
        
        results = await retriever.search_similar("doc1", max_results=2)
        
        assert len(results) == 2  # Excludes the source document
        assert results[0]["document_id"] == "doc2"
        assert results[1]["document_id"] == "doc3"

@pytest.mark.asyncio
async def test_search_similar_nonexistent_document(retriever):
    """Test similar search for non-existent document"""
    with patch.object(retriever.client, 'get_or_create_collection') as mock_collection:
        mock_collection.return_value.get.return_value = {
            'ids': [],
            'embeddings': [],
            'metadatas': [],
            'documents': []
        }
        
        with pytest.raises(ValueError, match="Document .* not found"):
            await retriever.search_similar("nonexistent")

@pytest.mark.asyncio
async def test_document_count_by_role(retriever):
    """Test document count based on user role"""
    with patch.object(retriever.client, 'get_or_create_collection') as mock_collection:
        mock_collection.return_value.count.return_value = 100
        mock_collection.return_value.get.return_value = {
            'metadatas': [
                {'category': 'service'},
                {'category': 'service'},
                {'category': 'rnd'},
                {'category': 'archive'},
            ]
        }
        
        # Test admin count (all categories)
        admin_count = await retriever.get_document_count("admin")
        assert admin_count["total"] == 4
        assert admin_count["by_category"]["service"] == 2
        assert admin_count["by_category"]["rnd"] == 1
        assert admin_count["by_category"]["archive"] == 1
        
        # Test service count (only service category)
        service_count = await retriever.get_document_count("service")
        assert service_count["total"] == 2
        assert service_count["by_category"]["service"] == 2
        assert "rnd" not in service_count["by_category"]

@pytest.mark.asyncio
async def test_llm_generation_error_handling(retriever):
    """Test error handling in LLM generation"""
    with patch.object(retriever, '_generate_sync', side_effect=Exception("LLM Error")):
        response = await retriever._generate_response("test query", "test context")
        
        assert "encountered an error" in response
        assert "LLM Error" in response

def test_prompt_formatting(retriever):
    """Test prompt template formatting"""
    context = "This is the context"
    question = "What is the answer?"
    
    formatted = retriever.prompt.format(context=context, question=question)
    
    assert context in formatted
    assert question in formatted
    assert "Context:" in formatted
    assert "Question:" in formatted