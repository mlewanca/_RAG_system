#!/usr/bin/env python3
"""
Example script showing how to use the RAG training system
Demonstrates feedback collection, processing, and model improvement
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.feedback_trainer import RAGTrainer, ResponseImprover

async def demo_feedback_collection():
    """Demonstrate feedback collection and processing"""
    
    print("🧠 RAG Training System Demo")
    print("=" * 40)
    
    # Initialize trainer
    config = RAGConfig()
    trainer = RAGTrainer(config)
    
    print("\n1️⃣ Collecting Sample Feedback")
    print("-" * 30)
    
    # Simulate user feedback scenarios
    feedback_examples = [
        {
            "query": "What are the security policies?",
            "response": "The security policies include authentication and authorization.",
            "rating": 5,
            "feedback": "Perfect answer! Very clear and comprehensive.",
            "user_role": "admin"
        },
        {
            "query": "How do I reset my password?",
            "response": "Contact your administrator.",
            "rating": 2,
            "feedback": "This is not helpful. I need step-by-step instructions.",
            "expected_response": "To reset your password: 1. Go to login page 2. Click 'Forgot Password' 3. Enter your email 4. Check your email for reset link 5. Follow the instructions in the email",
            "user_role": "service"
        },
        {
            "query": "What document formats are supported?",
            "response": "We support PDF, DOCX, TXT, and MD files.",
            "rating": 4,
            "feedback": "Good answer but could mention file size limits.",
            "user_role": "developer"
        },
        {
            "query": "How to upload a document?",
            "response": "Use the upload feature in the web interface.",
            "rating": 1,
            "feedback": "Too vague. Need detailed instructions.",
            "expected_response": "To upload a document: 1. Go to the 'Upload Document' page 2. Click 'Choose a file' 3. Select your document 4. Choose the appropriate category 5. Click 'Upload Document' 6. Wait for processing to complete",
            "user_role": "service"
        }
    ]
    
    feedback_ids = []
    for example in feedback_examples:
        feedback_id = trainer.collect_feedback(
            query=example["query"],
            response=example["response"],
            rating=example["rating"],
            feedback=example["feedback"],
            expected_response=example.get("expected_response"),
            user_role=example["user_role"]
        )
        
        if feedback_id:
            feedback_ids.append(feedback_id)
            print(f"✅ Collected feedback: {feedback_id}")
            print(f"   Query: {example['query']}")
            print(f"   Rating: {'⭐' * example['rating']}")
            print(f"   Feedback: {example['feedback']}")
            if example.get("expected_response"):
                print(f"   Expected: {example['expected_response'][:50]}...")
            print()
    
    print(f"📊 Total feedback collected: {len(feedback_ids)}")
    
    print("\n2️⃣ Processing Feedback into Training Data")
    print("-" * 45)
    
    processed_count = trainer.process_feedback_to_training_data()
    print(f"✅ Processed {processed_count} feedback entries into training data")
    
    print("\n3️⃣ Training System Statistics")
    print("-" * 35)
    
    stats = trainer.get_training_stats()
    
    print("📊 Feedback Statistics:")
    feedback_stats = stats.get('feedback', {})
    print(f"   • Total Feedback: {feedback_stats.get('total', 0)}")
    print(f"   • Processed: {feedback_stats.get('processed', 0)}")
    print(f"   • Average Rating: {feedback_stats.get('avg_rating', 0):.1f}⭐")
    print(f"   • Positive Feedback: {feedback_stats.get('positive', 0)}")
    print(f"   • Negative Feedback: {feedback_stats.get('negative', 0)}")
    
    print("\n🎯 Training Data Statistics:")
    training_stats = stats.get('training_data', {})
    print(f"   • Total Training Pairs: {training_stats.get('total_pairs', 0)}")
    print(f"   • Average Quality: {training_stats.get('avg_quality', 0):.1f}/5")
    print(f"   • Data Sources: {training_stats.get('sources', 0)}")
    print(f"   • Latest Update: {training_stats.get('latest_update', 'N/A')}")
    
    print("\n4️⃣ Exporting Training Data")
    print("-" * 32)
    
    try:
        # Export as JSONL (preferred for model training)
        jsonl_file = trainer.export_training_data(format="jsonl", min_quality=3.0)
        print(f"✅ JSONL export: {jsonl_file}")
        
        # Export as CSV (for analysis)
        csv_file = trainer.export_training_data(format="csv", min_quality=2.0)
        print(f"✅ CSV export: {csv_file}")
        
        # Show sample training data
        print("\n📋 Sample Training Data:")
        training_data = trainer.db.get_training_data(min_quality=3.0, limit=2)
        
        for i, pair in enumerate(training_data[:2], 1):
            print(f"\n   Example {i}:")
            print(f"   Input: {pair.input_text}")
            print(f"   Output: {pair.output_text[:100]}...")
            print(f"   Quality: {pair.quality_score}/5")
            print(f"   Source: {pair.source}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
    
    print("\n5️⃣ Response Improvement Demo")
    print("-" * 35)
    
    # Test response improvement
    improver = ResponseImprover(config)
    
    test_queries = [
        "How do I reset my password?",
        "What document formats are supported?",
        "How to upload a document?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing: '{query}'")
        
        # Simulate a basic response
        basic_response = f"Here's information about {query.lower()}"
        
        # Try to improve it
        improved_response, confidence = improver.improve_response(query, basic_response)
        
        if confidence > 0.5:
            print(f"✨ Improved response (confidence: {confidence:.2f}):")
            print(f"   {improved_response[:100]}...")
        else:
            print(f"📝 No improvement available (confidence: {confidence:.2f})")
            print(f"   Original: {basic_response}")
    
    print("\n6️⃣ Creating Synthetic Training Data")
    print("-" * 40)
    
    # Add some known good examples
    synthetic_queries = [
        "What is the RAG system?",
        "How does document indexing work?",
        "What are user roles and permissions?"
    ]
    
    synthetic_responses = [
        "The RAG (Retrieval-Augmented Generation) system combines document retrieval with AI generation to provide accurate, contextual answers based on your document collection.",
        "Document indexing works by processing uploaded documents, extracting text content, splitting it into chunks, generating embeddings, and storing them in a vector database for semantic search.",
        "User roles define access permissions: 'service' users access basic documents, 'developer' users can access service and R&D documents, 'admin' users have full system access including user management and document upload capabilities."
    ]
    
    synthetic_count = trainer.create_synthetic_training_data(
        queries=synthetic_queries,
        responses=synthetic_responses
    )
    
    print(f"✅ Created {synthetic_count} synthetic training pairs")
    
    # Updated stats
    updated_stats = trainer.get_training_stats()
    training_stats = updated_stats.get('training_data', {})
    print(f"📊 Total training pairs now: {training_stats.get('total_pairs', 0)}")
    
    print("\n🎉 Training Demo Complete!")
    print("=" * 30)
    print("""
Next Steps for Production:
1. Encourage users to provide feedback through the web interface
2. Regularly process feedback (weekly/monthly) via admin panel
3. Export high-quality training data (>4.0 rating)
4. Use exported data to fine-tune your language model
5. Monitor response quality and user satisfaction over time

The system will automatically improve responses using stored training data!
    """)

if __name__ == "__main__":
    asyncio.run(demo_feedback_collection())