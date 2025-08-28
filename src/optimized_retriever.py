"""Optimized retriever with hybrid search, caching, and query expansion"""

import logging
import asyncio
import hashlib
import json
import time
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import sys
import os
from pathlib import Path
import redis
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.roles import ROLE_PERMISSIONS, get_role_permissions

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    content: str
    metadata: Dict[str, Any]
    vector_score: float
    keyword_score: float
    combined_score: float
    retrieved_at: str

class QueryCache:
    """Redis-based caching for embeddings and responses"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.embedding_ttl = 3600  # 1 hour
            self.response_ttl = 1800   # 30 minutes
            self.redis.ping()  # Test connection
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            self.redis = None
    
    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        if not self.redis:
            return None
        
        try:
            cache_key = f"emb:{hashlib.md5(text.encode()).hexdigest()}"
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def cache_embedding(self, text: str, embedding: List[float]):
        if not self.redis:
            return
        
        try:
            cache_key = f"emb:{hashlib.md5(text.encode()).hexdigest()}"
            self.redis.setex(cache_key, self.embedding_ttl, json.dumps(embedding))
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def get_cached_response(self, query_hash: str, user_role: str) -> Optional[Dict]:
        if not self.redis:
            return None
        
        try:
            cache_key = f"resp:{query_hash}:{user_role}"
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Response cache get error: {e}")
        return None
    
    async def cache_response(self, query_hash: str, user_role: str, response: Dict):
        if not self.redis:
            return
        
        try:
            cache_key = f"resp:{query_hash}:{user_role}"
            self.redis.setex(cache_key, self.response_ttl, json.dumps(response, default=str))
        except Exception as e:
            logger.error(f"Response cache set error: {e}")

class QueryExpander:
    """LLM-based query expansion for better retrieval"""
    
    def __init__(self, llm: OllamaLLM):
        self.llm = llm
        self.expansion_prompt = PromptTemplate(
            template="""Given the original query and user role, generate alternative phrasings and related terms that might help find relevant documents.

Original query: {query}
User role: {role}

Generate:
1. 2 alternative phrasings of the same question
2. 2 related technical terms or concepts
3. 1 broader category this query might belong to

Format as JSON:
{{"alternatives": [], "terms": [], "category": ""}}""",
            input_variables=["query", "role"]
        )
    
    async def expand_query(self, query: str, user_role: str) -> Dict[str, List[str]]:
        """Expand query with alternatives and related terms"""
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                prompt = self.expansion_prompt.format(query=query, role=user_role)
                response = await loop.run_in_executor(executor, self.llm.invoke, prompt)
                
                # Parse JSON response
                try:
                    expansion = json.loads(response)
                    return {
                        'original': query,
                        'alternatives': expansion.get('alternatives', []),
                        'terms': expansion.get('terms', []),
                        'category': expansion.get('category', ''),
                        'all_queries': [query] + expansion.get('alternatives', []) + expansion.get('terms', [])
                    }
                except json.JSONDecodeError:
                    logger.warning("Failed to parse query expansion JSON")
                    return {'original': query, 'alternatives': [], 'terms': [], 'category': '', 'all_queries': [query]}
                    
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return {'original': query, 'alternatives': [], 'terms': [], 'category': '', 'all_queries': [query]}

class HybridRetriever:
    """Enhanced retriever with vector + keyword search, caching, and optimization"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize components
        self.embeddings = OllamaEmbeddings(
            model=config.embedding_model,
            base_url=config.ollama_base_url
        )
        
        self.llm = OllamaLLM(
            model=config.generation_model,
            base_url=config.ollama_base_url,
            temperature=0.7,
            num_predict=512
        )
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(config.chroma_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection_name = "rag_documents"
        
        # Initialize caching and optimization
        self.cache = QueryCache()
        self.query_expander = QueryExpander(self.llm)
        
        # TF-IDF for keyword search
        self.tfidf_vectorizer = None
        self.document_cache = {}
        self._initialize_keyword_search()
        
        # Scoring weights
        self.vector_weight = 0.7
        self.keyword_weight = 0.3
        
        # Performance tracking
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_query_time': 0,
            'total_queries': 0
        }
        
        logger.info("Optimized hybrid retriever initialized")
    
    def _initialize_keyword_search(self):
        """Initialize TF-IDF vectorizer for keyword search"""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Get all documents for TF-IDF
            if collection.count() > 0:
                all_docs = collection.get(
                    limit=collection.count(),
                    include=["documents"]
                )
                
                documents = all_docs.get('documents', [])
                if documents:
                    self.tfidf_vectorizer = TfidfVectorizer(
                        max_features=5000,
                        stop_words='english',
                        ngram_range=(1, 2)
                    )
                    self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
                    self.document_cache = {i: doc for i, doc in enumerate(documents)}
                    logger.info(f"TF-IDF initialized with {len(documents)} documents")
                else:
                    logger.info("No documents found for TF-IDF initialization")
            else:
                logger.info("Empty collection, TF-IDF will be initialized when documents are added")
                
        except Exception as e:
            logger.error(f"TF-IDF initialization failed: {e}")
            self.tfidf_vectorizer = None
    
    async def get_embedding_cached(self, text: str) -> List[float]:
        """Get embedding with caching"""
        # Try cache first
        cached_embedding = await self.cache.get_cached_embedding(text)
        if cached_embedding:
            self.metrics['cache_hits'] += 1
            return cached_embedding
        
        # Generate embedding
        self.metrics['cache_misses'] += 1
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            embedding = await loop.run_in_executor(
                executor, self.embeddings.embed_query, text
            )
        
        # Cache the result
        await self.cache.cache_embedding(text, embedding)
        return embedding
    
    async def vector_search(self, query: str, max_results: int, user_role: str) -> List[QueryResult]:
        """Perform vector similarity search"""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Get role-based filters
            role_permissions = get_role_permissions(user_role)
            role_filters = {}
            if len(role_permissions) == 1:
                role_filters = {"category": role_permissions[0]}
            elif len(role_permissions) > 1:
                role_filters = {"$or": [{"category": cat} for cat in role_permissions]}
            
            # Generate query embedding
            query_embedding = await self.get_embedding_cached(query)
            
            # Search
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": max_results,
                "include": ["metadatas", "documents", "distances"]
            }
            
            if role_filters and collection.count() > 0:
                query_params["where"] = role_filters
            
            results = collection.query(**query_params)
            
            # Convert to QueryResult objects
            query_results = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    vector_score = 1 - results['distances'][0][i]  # Convert distance to similarity
                    
                    query_results.append(QueryResult(
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i],
                        vector_score=vector_score,
                        keyword_score=0.0,  # Will be filled by keyword search
                        combined_score=vector_score,  # Will be updated
                        retrieved_at=datetime.utcnow().isoformat()
                    ))
            
            return query_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def keyword_search(self, query: str, max_results: int) -> Dict[int, float]:
        """Perform TF-IDF keyword search"""
        if not self.tfidf_vectorizer:
            return {}
        
        try:
            # Transform query
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top results
            top_indices = similarities.argsort()[-max_results:][::-1]
            
            # Return as dict of index: score
            return {idx: similarities[idx] for idx in top_indices if similarities[idx] > 0}
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return {}
    
    def combine_scores(self, vector_results: List[QueryResult], 
                      keyword_scores: Dict[int, float]) -> List[QueryResult]:
        """Combine vector and keyword scores"""
        # Create a mapping of content to keyword scores
        content_keyword_scores = {}
        for idx, score in keyword_scores.items():
            if idx < len(self.document_cache):
                content = self.document_cache[idx]
                content_keyword_scores[content] = score
        
        # Update vector results with keyword scores
        for result in vector_results:
            keyword_score = content_keyword_scores.get(result.content, 0.0)
            result.keyword_score = keyword_score
            result.combined_score = (
                self.vector_weight * result.vector_score + 
                self.keyword_weight * keyword_score
            )
        
        # Sort by combined score
        vector_results.sort(key=lambda x: x.combined_score, reverse=True)
        return vector_results
    
    async def hybrid_search(self, query: str, max_results: int, user_role: str) -> List[QueryResult]:
        """Perform hybrid vector + keyword search"""
        try:
            # Parallel search
            vector_task = asyncio.create_task(
                self.vector_search(query, max_results * 2, user_role)
            )
            keyword_task = asyncio.create_task(
                self.keyword_search(query, max_results * 2)
            )
            
            vector_results, keyword_scores = await asyncio.gather(vector_task, keyword_task)
            
            # Combine scores
            combined_results = self.combine_scores(vector_results, keyword_scores)
            
            return combined_results[:max_results]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return await self.vector_search(query, max_results, user_role)
    
    async def query_with_expansion(self, query: str, max_results: int, user_role: str,
                                 use_expansion: bool = True) -> List[QueryResult]:
        """Query with optional expansion"""
        if not use_expansion:
            return await self.hybrid_search(query, max_results, user_role)
        
        try:
            # Expand query
            expansion = await self.query_expander.expand_query(query, user_role)
            
            # Search with all expanded queries
            all_results = []
            for expanded_query in expansion['all_queries']:
                results = await self.hybrid_search(expanded_query, max_results // 2, user_role)
                all_results.extend(results)
            
            # Deduplicate and re-rank
            seen_content = set()
            unique_results = []
            for result in all_results:
                if result.content not in seen_content:
                    seen_content.add(result.content)
                    unique_results.append(result)
            
            # Sort by combined score and return top results
            unique_results.sort(key=lambda x: x.combined_score, reverse=True)
            return unique_results[:max_results]
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return await self.hybrid_search(query, max_results, user_role)
    
    async def generate_response(self, query: str, context_results: List[QueryResult]) -> str:
        """Generate response with optimized context"""
        try:
            # Prepare optimized context (top 3 most relevant)
            context_parts = []
            for result in context_results[:3]:
                context_parts.append(f"[Score: {result.combined_score:.3f}] {result.content}")
            
            context = "\n\n".join(context_parts)
            
            # Generate response
            prompt = f"""You are a helpful AI assistant. Use the following context to answer the question. If you cannot answer based on the context, say so clearly.

Context:
{context}

Question: {query}

Answer:"""
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, self.llm.invoke, prompt)
                
            return response
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return f"I found relevant documents but encountered an error generating a response: {str(e)}"
    
    async def query(self, query: str, max_results: int = 5, user_role: str = "service",
                   use_expansion: bool = True, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Main query interface with all optimizations"""
        start_time = time.time()
        
        try:
            # Check response cache
            query_hash = hashlib.md5(f"{query}:{max_results}:{user_role}".encode()).hexdigest()
            if use_cache:
                cached_response = await self.cache.get_cached_response(query_hash, user_role)
                if cached_response:
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    return cached_response
            
            # Perform optimized search
            results = await self.query_with_expansion(query, max_results, user_role, use_expansion)
            
            if not results:
                response_data = [{
                    "content": "No relevant documents found for your query.",
                    "metadata": {"type": "no_results"},
                    "score": 0.0,
                    "search_type": "hybrid"
                }]
            else:
                # Generate augmented response
                generated_response = await self.generate_response(query, results)
                
                # Format results
                response_data = [{
                    "content": generated_response,
                    "metadata": {
                        "type": "generated",
                        "model": self.config.generation_model,
                        "source_documents": len(results),
                        "search_type": "hybrid_expanded" if use_expansion else "hybrid"
                    },
                    "score": 1.0,
                    "generated_at": datetime.utcnow().isoformat()
                }]
                
                # Add source documents
                for result in results:
                    response_data.append({
                        "content": result.content,
                        "metadata": result.metadata,
                        "score": result.combined_score,
                        "vector_score": result.vector_score,
                        "keyword_score": result.keyword_score,
                        "retrieved_at": result.retrieved_at
                    })
            
            # Cache response
            if use_cache:
                await self.cache.cache_response(query_hash, user_role, response_data)
            
            # Update metrics
            query_time = time.time() - start_time
            self.metrics['total_queries'] += 1
            self.metrics['avg_query_time'] = (
                (self.metrics['avg_query_time'] * (self.metrics['total_queries'] - 1) + query_time) / 
                self.metrics['total_queries']
            )
            
            logger.info(f"Optimized query processed in {query_time:.3f}s, returning {len(response_data)} results")
            return response_data
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (self.metrics['cache_hits'] / cache_total) if cache_total > 0 else 0
        
        return {
            **self.metrics,
            'cache_hit_rate': cache_hit_rate,
            'redis_connected': self.cache.redis is not None
        }