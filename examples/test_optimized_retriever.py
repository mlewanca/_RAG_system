#!/usr/bin/env python3
"""
Test script for the optimized retriever functionality
Demonstrates hybrid search, caching, and query expansion features
"""

import asyncio
import time
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.enhanced_retriever import EnhancedRetriever
from src.optimized_retriever import HybridRetriever

async def test_retriever_performance():
    """Compare performance between standard and optimized retrievers"""
    
    # Initialize configuration
    config = RAGConfig()
    
    # Initialize both retrievers
    standard_retriever = EnhancedRetriever(config)
    optimized_retriever = HybridRetriever(config)
    
    # Test queries
    test_queries = [
        "What are the security policies for document access?",
        "How to configure the RAG system?",
        "What are the user roles and permissions?",
        "How to upload documents to the system?",
        "What is the authentication process?"
    ]
    
    print("🧪 RAG Retriever Performance Comparison")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test Query {i}: {query}")
        print("-" * 40)
        
        # Test standard retriever
        start_time = time.time()
        try:
            standard_results = await standard_retriever.query(
                query=query,
                max_results=3,
                user_role="admin"
            )
            standard_time = time.time() - start_time
            standard_count = len(standard_results)
            print(f"📊 Standard Retriever: {standard_time:.3f}s, {standard_count} results")
        except Exception as e:
            print(f"❌ Standard Retriever Error: {e}")
            standard_time = None
            standard_count = 0
        
        # Test optimized retriever
        start_time = time.time()
        try:
            optimized_results = await optimized_retriever.query(
                query=query,
                max_results=3,
                user_role="admin",
                use_expansion=True,
                use_cache=True
            )
            optimized_time = time.time() - start_time
            optimized_count = len(optimized_results)
            print(f"🚀 Optimized Retriever: {optimized_time:.3f}s, {optimized_count} results")
            
            # Show additional metrics
            if hasattr(optimized_retriever, 'get_metrics'):
                metrics = optimized_retriever.get_metrics()
                print(f"📈 Cache Hit Rate: {metrics.get('cache_hit_rate', 0):.2%}")
                print(f"🔗 Redis Connected: {metrics.get('redis_connected', False)}")
                
        except Exception as e:
            print(f"❌ Optimized Retriever Error: {e}")
            optimized_time = None
            optimized_count = 0
        
        # Performance comparison
        if standard_time and optimized_time:
            improvement = ((standard_time - optimized_time) / standard_time) * 100
            print(f"⚡ Speed Improvement: {improvement:.1f}%")
        
        # Second run to test caching
        print("🔄 Testing cache performance...")
        start_time = time.time()
        try:
            cached_results = await optimized_retriever.query(
                query=query,
                max_results=3,
                user_role="admin",
                use_expansion=True,
                use_cache=True
            )
            cached_time = time.time() - start_time
            print(f"💾 Cached Query: {cached_time:.3f}s")
            
            if optimized_time:
                cache_improvement = ((optimized_time - cached_time) / optimized_time) * 100
                print(f"📈 Cache Speed Boost: {cache_improvement:.1f}%")
                
        except Exception as e:
            print(f"❌ Cache Test Error: {e}")

async def test_query_expansion():
    """Test query expansion functionality"""
    
    print("\n🔍 Query Expansion Test")
    print("=" * 30)
    
    config = RAGConfig()
    retriever = HybridRetriever(config)
    
    test_query = "user permissions"
    print(f"Original Query: '{test_query}'")
    
    try:
        # Test expansion
        expansion = await retriever.query_expander.expand_query(test_query, "admin")
        
        print(f"\n📋 Query Expansion Results:")
        print(f"  • Original: {expansion['original']}")
        print(f"  • Alternatives: {expansion['alternatives']}")
        print(f"  • Related Terms: {expansion['terms']}")
        print(f"  • Category: {expansion['category']}")
        print(f"  • All Queries: {expansion['all_queries']}")
        
    except Exception as e:
        print(f"❌ Query Expansion Error: {e}")

async def test_hybrid_search():
    """Test hybrid search functionality"""
    
    print("\n🔀 Hybrid Search Test")
    print("=" * 25)
    
    config = RAGConfig()
    retriever = HybridRetriever(config)
    
    test_query = "document security"
    
    try:
        # Test vector search only
        print("🔍 Vector Search:")
        vector_results = await retriever.vector_search(test_query, 3, "admin")
        for i, result in enumerate(vector_results[:3], 1):
            print(f"  {i}. Score: {result.vector_score:.3f} | {result.content[:50]}...")
        
        # Test keyword search
        print("\n🔤 Keyword Search:")
        keyword_scores = await retriever.keyword_search(test_query, 3)
        print(f"  Found {len(keyword_scores)} keyword matches")
        
        # Test hybrid search
        print("\n🚀 Hybrid Search:")
        hybrid_results = await retriever.hybrid_search(test_query, 3, "admin")
        for i, result in enumerate(hybrid_results[:3], 1):
            print(f"  {i}. Vector: {result.vector_score:.3f}, Keyword: {result.keyword_score:.3f}, Combined: {result.combined_score:.3f}")
            print(f"     Content: {result.content[:50]}...")
        
    except Exception as e:
        print(f"❌ Hybrid Search Error: {e}")

async def test_caching_system():
    """Test caching system functionality"""
    
    print("\n💾 Caching System Test")
    print("=" * 25)
    
    config = RAGConfig()
    retriever = HybridRetriever(config)
    
    test_text = "This is a test document for embedding caching"
    
    try:
        # Test embedding cache
        print("🧠 Testing Embedding Cache:")
        
        # First call - should miss cache
        start_time = time.time()
        embedding1 = await retriever.get_embedding_cached(test_text)
        time1 = time.time() - start_time
        print(f"  First call (cache miss): {time1:.3f}s")
        
        # Second call - should hit cache
        start_time = time.time()
        embedding2 = await retriever.get_embedding_cached(test_text)
        time2 = time.time() - start_time
        print(f"  Second call (cache hit): {time2:.3f}s")
        
        # Verify embeddings are the same
        if embedding1 == embedding2:
            print("  ✅ Cached embedding matches original")
            cache_speedup = ((time1 - time2) / time1) * 100
            print(f"  📈 Cache speedup: {cache_speedup:.1f}%")
        else:
            print("  ❌ Cached embedding differs from original")
        
        # Show cache metrics
        metrics = retriever.get_metrics()
        print(f"\n📊 Cache Metrics:")
        print(f"  • Cache Hits: {metrics.get('cache_hits', 0)}")
        print(f"  • Cache Misses: {metrics.get('cache_misses', 0)}")
        print(f"  • Hit Rate: {metrics.get('cache_hit_rate', 0):.2%}")
        print(f"  • Redis Connected: {metrics.get('redis_connected', False)}")
        
    except Exception as e:
        print(f"❌ Caching Test Error: {e}")

async def main():
    """Run all tests"""
    
    print("🚀 RAG System Optimization Tests")
    print("=" * 40)
    
    try:
        await test_retriever_performance()
        await test_query_expansion()
        await test_hybrid_search()
        await test_caching_system()
        
        print("\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n⏸️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())