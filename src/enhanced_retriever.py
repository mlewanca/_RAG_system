"""Enhanced retriever with role-based filtering and advanced search"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import chromadb
from chromadb.config import Settings

from config.roles import ROLE_PERMISSIONS, get_role_permissions

logger = logging.getLogger(__name__)

class EnhancedRetriever:
    def __init__(self, config):
        self.config = config
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(
            model=config.embedding_model,
            base_url=config.ollama_base_url
        )
        
        # Initialize LLM
        self.llm = OllamaLLM(
            model=config.generation_model,
            base_url=config.ollama_base_url,
            temperature=0.7,
            num_predict=512
        )
        
        # Initialize ChromaDB client with explicit settings to avoid conflicts
        self.client = chromadb.PersistentClient(
            path=str(config.chroma_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.collection_name = "rag_documents"
        
        # Use role permissions from central configuration
        self.role_permissions = ROLE_PERMISSIONS
        
        # Initialize prompt template
        self.prompt_template = """You are a helpful AI assistant with access to a document database.
        Use the following context to answer the question. If you cannot answer based on the context,
        say so clearly.

        Context: {context}

        Question: {question}

        Answer: """
        
        self.prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question"]
        )
        
        logger.info("Enhanced retriever initialized")
    
    def get_user_filters(self, user_role: str) -> Dict[str, Any]:
        """Get document filters based on user role"""
        allowed_categories = get_role_permissions(user_role)
        
        # Build filter for allowed document categories
        if len(allowed_categories) == 1:
            # If only one category, use direct filter
            filters = {"category": allowed_categories[0]}
        elif len(allowed_categories) > 1:
            # If multiple categories, use $or
            filters = {
                "$or": [
                    {"category": cat} for cat in allowed_categories
                ]
            }
        else:
            # If no categories allowed, return empty filter
            filters = {}
        
        return filters
    
    async def query(
        self,
        query: str,
        max_results: int = 5,
        user_role: str = "service",
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Perform role-based document retrieval and generation"""
        try:
            logger.info(f"Processing query: '{query}' for role: {user_role}")
            
            # Get collection
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Combine role-based filters with custom filters
            role_filters = self.get_user_filters(user_role)
            if filters:
                combined_filters = {"$and": [role_filters, filters]}
            else:
                combined_filters = role_filters
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search similar documents
            # Only apply filters if they're not empty
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": max_results,
                "include": ["metadatas", "documents", "distances"]
            }
            
            # Only add where clause if we have filters and documents
            if combined_filters and collection.count() > 0:
                # Check if filters are not empty dict
                if combined_filters != {}:
                    query_params["where"] = combined_filters
            
            results = collection.query(**query_params)
            
            if not results['ids'][0]:
                logger.info("No matching documents found")
                return [{
                    "content": "No relevant documents found for your query.",
                    "metadata": {},
                    "score": 0.0
                }]
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "score": 1 - results['distances'][0][i],  # Convert distance to similarity score
                    "retrieved_at": datetime.utcnow().isoformat()
                }
                formatted_results.append(result)
            
            # Generate augmented response using LLM
            context = "\n\n".join([r['content'] for r in formatted_results[:3]])
            
            augmented_response = await self._generate_response(query, context)
            
            # Add augmented response as the first result
            formatted_results.insert(0, {
                "content": augmented_response,
                "metadata": {
                    "type": "generated",
                    "model": self.config.generation_model,
                    "source_documents": len(formatted_results)
                },
                "score": 1.0,
                "generated_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Query processed successfully, returning {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise
    
    async def _generate_response(self, query: str, context: str) -> str:
        """Generate response using LLM"""
        try:
            # Run LLM generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(
                    executor,
                    self._generate_sync,
                    query,
                    context
                )
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I found relevant documents but encountered an error generating a response: {str(e)}"
    
    def _generate_sync(self, query: str, context: str) -> str:
        """Synchronous generation for thread pool"""
        formatted_prompt = self.prompt.format(
            context=context,
            question=query
        )
        return self.llm.invoke(formatted_prompt)
    
    async def search_similar(
        self,
        document_id: str,
        max_results: int = 5,
        user_role: str = "service"
    ) -> List[Dict[str, Any]]:
        """Find documents similar to a given document"""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Get the document
            doc_result = collection.get(
                ids=[document_id],
                include=["embeddings", "metadatas", "documents"]
            )
            
            if not doc_result['ids']:
                raise ValueError(f"Document {document_id} not found")
            
            # Use the document's embedding to find similar documents
            embedding = doc_result['embeddings'][0]
            
            # Get role-based filters
            role_filters = self.get_user_filters(user_role)
            
            # Search for similar documents
            results = collection.query(
                query_embeddings=[embedding],
                n_results=max_results + 1,  # +1 to exclude the source document
                where=role_filters,
                include=["metadatas", "documents", "distances"]
            )
            
            # Format and filter results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                if results['ids'][0][i] != document_id:  # Exclude source document
                    result = {
                        "document_id": results['ids'][0][i],
                        "content": results['documents'][0][i][:200] + "...",  # Preview
                        "metadata": results['metadatas'][0][i],
                        "similarity_score": 1 - results['distances'][0][i]
                    }
                    formatted_results.append(result)
            
            return formatted_results[:max_results]
            
        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            raise
    
    async def get_document_count(self, user_role: str = "service") -> Dict[str, int]:
        """Get count of accessible documents by category"""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Get all documents with minimal data
            all_docs = collection.get(
                limit=collection.count(),
                include=["metadatas"]
            )
            
            # Count by category based on user role
            allowed_categories = self.role_permissions.get(user_role, ["service"])
            category_counts = {cat: 0 for cat in allowed_categories}
            
            for metadata in all_docs.get('metadatas', []):
                if metadata:
                    category = metadata.get('category', 'service')
                    if category in category_counts:
                        category_counts[category] += 1
            
            return {
                "total": sum(category_counts.values()),
                "by_category": category_counts,
                "user_role": user_role
            }
            
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            raise
