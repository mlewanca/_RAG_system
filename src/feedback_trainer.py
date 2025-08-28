"""
RAG Training System - Collect feedback and improve responses
Supports multiple training approaches from simple prompt engineering to model fine-tuning
"""

import logging
import json
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import asyncio
from dataclasses import dataclass, asdict
import pandas as pd
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEntry:
    """Structure for storing user feedback"""
    id: str
    query: str
    response: str
    user_rating: int  # 1-5 scale
    user_feedback: str
    expected_response: Optional[str] = None
    helpful_results: List[str] = None
    user_role: str = "service"
    timestamp: str = None
    processed: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.helpful_results is None:
            self.helpful_results = []

@dataclass
class TrainingPair:
    """Structure for training data"""
    instruction: str
    input_text: str
    output_text: str
    quality_score: float
    source: str  # "feedback", "synthetic", "curated"
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

class FeedbackDatabase:
    """SQLite database for storing training feedback"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    user_rating INTEGER,
                    user_feedback TEXT,
                    expected_response TEXT,
                    helpful_results TEXT,  -- JSON array
                    user_role TEXT,
                    timestamp TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_pairs (
                    id TEXT PRIMARY KEY,
                    instruction TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    output_text TEXT NOT NULL,
                    quality_score REAL,
                    source TEXT,
                    created_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT,
                    test_queries TEXT,  -- JSON array
                    avg_rating REAL,
                    improvement_score REAL,
                    training_date TEXT
                )
            """)
    
    def add_feedback(self, feedback: FeedbackEntry) -> bool:
        """Add feedback entry to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO feedback 
                    (id, query, response, user_rating, user_feedback, expected_response,
                     helpful_results, user_role, timestamp, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback.id, feedback.query, feedback.response,
                    feedback.user_rating, feedback.user_feedback,
                    feedback.expected_response,
                    json.dumps(feedback.helpful_results),
                    feedback.user_role, feedback.timestamp, feedback.processed
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to add feedback: {e}")
            return False
    
    def get_unprocessed_feedback(self) -> List[FeedbackEntry]:
        """Get all unprocessed feedback entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM feedback WHERE processed = FALSE
                    ORDER BY timestamp DESC
                """)
                
                entries = []
                for row in cursor.fetchall():
                    entry = FeedbackEntry(
                        id=row[0], query=row[1], response=row[2],
                        user_rating=row[3], user_feedback=row[4],
                        expected_response=row[5],
                        helpful_results=json.loads(row[6]) if row[6] else [],
                        user_role=row[7], timestamp=row[8],
                        processed=bool(row[9])
                    )
                    entries.append(entry)
                
                return entries
        except Exception as e:
            logger.error(f"Failed to get feedback: {e}")
            return []
    
    def add_training_pair(self, pair: TrainingPair) -> bool:
        """Add training pair to database"""
        try:
            pair_id = hashlib.md5(f"{pair.input_text}:{pair.output_text}".encode()).hexdigest()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO training_pairs
                    (id, instruction, input_text, output_text, quality_score, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pair_id, pair.instruction, pair.input_text,
                    pair.output_text, pair.quality_score, pair.source,
                    pair.created_at
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to add training pair: {e}")
            return False
    
    def get_training_data(self, min_quality: float = 3.0, limit: int = 1000) -> List[TrainingPair]:
        """Get training pairs for model fine-tuning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM training_pairs 
                    WHERE quality_score >= ?
                    ORDER BY quality_score DESC, created_at DESC
                    LIMIT ?
                """, (min_quality, limit))
                
                pairs = []
                for row in cursor.fetchall():
                    pair = TrainingPair(
                        instruction=row[1], input_text=row[2], output_text=row[3],
                        quality_score=row[4], source=row[5], created_at=row[6]
                    )
                    pairs.append(pair)
                
                return pairs
        except Exception as e:
            logger.error(f"Failed to get training data: {e}")
            return []
    
    def mark_processed(self, feedback_ids: List[str]):
        """Mark feedback entries as processed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ','.join(['?' for _ in feedback_ids])
                conn.execute(f"""
                    UPDATE feedback SET processed = TRUE
                    WHERE id IN ({placeholders})
                """, feedback_ids)
        except Exception as e:
            logger.error(f"Failed to mark processed: {e}")

class RAGTrainer:
    """Main training system for RAG improvements"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.db = FeedbackDatabase(str(Path(config.base_dir) / "training" / "feedback.db"))
        self.training_dir = Path(config.base_dir) / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("RAG Trainer initialized")
    
    def collect_feedback(self, query: str, response: str, rating: int,
                        feedback: str, expected_response: str = None,
                        helpful_results: List[str] = None, user_role: str = "service") -> str:
        """Collect user feedback for a query-response pair"""
        
        # Generate unique ID for this feedback
        feedback_id = hashlib.md5(
            f"{query}:{response}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        
        feedback_entry = FeedbackEntry(
            id=feedback_id,
            query=query,
            response=response,
            user_rating=rating,
            user_feedback=feedback,
            expected_response=expected_response,
            helpful_results=helpful_results or [],
            user_role=user_role
        )
        
        success = self.db.add_feedback(feedback_entry)
        if success:
            logger.info(f"Feedback collected: {feedback_id}")
            return feedback_id
        else:
            logger.error("Failed to collect feedback")
            return None
    
    def process_feedback_to_training_data(self) -> int:
        """Convert feedback entries into training pairs"""
        
        unprocessed = self.db.get_unprocessed_feedback()
        processed_count = 0
        processed_ids = []
        
        for feedback in unprocessed:
            try:
                # Create training pairs based on feedback type
                
                # High-quality responses (rating 4-5)
                if feedback.user_rating >= 4:
                    pair = TrainingPair(
                        instruction="Answer the following question based on the provided context.",
                        input_text=f"Question: {feedback.query}",
                        output_text=feedback.response,
                        quality_score=float(feedback.user_rating),
                        source="positive_feedback"
                    )
                    self.db.add_training_pair(pair)
                    processed_count += 1
                
                # Corrected responses (user provided expected response)
                elif feedback.expected_response:
                    pair = TrainingPair(
                        instruction="Answer the following question based on the provided context.",
                        input_text=f"Question: {feedback.query}",
                        output_text=feedback.expected_response,
                        quality_score=5.0,  # User-corrected responses are high quality
                        source="user_correction"
                    )
                    self.db.add_training_pair(pair)
                    processed_count += 1
                
                # Negative feedback with improvement suggestions
                elif feedback.user_rating <= 2 and feedback.user_feedback:
                    # Create an improved response based on feedback
                    improved_response = self._generate_improved_response(
                        feedback.query, feedback.response, feedback.user_feedback
                    )
                    
                    if improved_response:
                        pair = TrainingPair(
                            instruction="Answer the following question based on the provided context.",
                            input_text=f"Question: {feedback.query}",
                            output_text=improved_response,
                            quality_score=3.5,  # Estimated quality
                            source="feedback_improvement"
                        )
                        self.db.add_training_pair(pair)
                        processed_count += 1
                
                processed_ids.append(feedback.id)
                
            except Exception as e:
                logger.error(f"Failed to process feedback {feedback.id}: {e}")
        
        # Mark all as processed
        if processed_ids:
            self.db.mark_processed(processed_ids)
        
        logger.info(f"Processed {processed_count} feedback entries into training data")
        return processed_count
    
    def _generate_improved_response(self, query: str, original_response: str,
                                  user_feedback: str) -> Optional[str]:
        """Generate improved response based on user feedback"""
        
        # This is a placeholder - in practice, you'd use your LLM to improve the response
        improvement_prompt = f"""
        Original Query: {query}
        Original Response: {original_response}
        User Feedback: {user_feedback}
        
        Please provide an improved response that addresses the user's feedback:
        """
        
        # For now, return a template - you'd integrate with your LLM here
        return f"Improved response for: {query} (addressing: {user_feedback})"
    
    def export_training_data(self, format: str = "jsonl", min_quality: float = 3.0) -> str:
        """Export training data for model fine-tuning"""
        
        training_data = self.db.get_training_data(min_quality=min_quality)
        
        if format.lower() == "jsonl":
            output_file = self.training_dir / f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            
            with open(output_file, 'w') as f:
                for pair in training_data:
                    training_entry = {
                        "instruction": pair.instruction,
                        "input": pair.input_text,
                        "output": pair.output_text,
                        "quality_score": pair.quality_score,
                        "source": pair.source
                    }
                    f.write(json.dumps(training_entry) + "\n")
            
            logger.info(f"Exported {len(training_data)} training pairs to {output_file}")
            return str(output_file)
        
        elif format.lower() == "csv":
            output_file = self.training_dir / f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            df = pd.DataFrame([asdict(pair) for pair in training_data])
            df.to_csv(output_file, index=False)
            
            logger.info(f"Exported {len(training_data)} training pairs to {output_file}")
            return str(output_file)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Get statistics about training data"""
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                # Feedback stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_feedback,
                        COUNT(CASE WHEN processed = TRUE THEN 1 END) as processed_feedback,
                        AVG(user_rating) as avg_rating,
                        COUNT(CASE WHEN user_rating >= 4 THEN 1 END) as positive_feedback,
                        COUNT(CASE WHEN user_rating <= 2 THEN 1 END) as negative_feedback
                    FROM feedback
                """)
                feedback_stats = cursor.fetchone()
                
                # Training data stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_pairs,
                        AVG(quality_score) as avg_quality,
                        COUNT(DISTINCT source) as sources,
                        MAX(created_at) as latest_training
                    FROM training_pairs
                """)
                training_stats = cursor.fetchone()
                
                return {
                    "feedback": {
                        "total": feedback_stats[0] or 0,
                        "processed": feedback_stats[1] or 0,
                        "avg_rating": round(feedback_stats[2] or 0, 2),
                        "positive": feedback_stats[3] or 0,
                        "negative": feedback_stats[4] or 0
                    },
                    "training_data": {
                        "total_pairs": training_stats[0] or 0,
                        "avg_quality": round(training_stats[1] or 0, 2),
                        "sources": training_stats[2] or 0,
                        "latest_update": training_stats[3]
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get training stats: {e}")
            return {"error": str(e)}
    
    def create_synthetic_training_data(self, queries: List[str],
                                     expected_responses: List[str]) -> int:
        """Create synthetic training data from known good examples"""
        
        if len(queries) != len(expected_responses):
            raise ValueError("Queries and responses must have same length")
        
        created_count = 0
        
        for query, response in zip(queries, expected_responses):
            pair = TrainingPair(
                instruction="Answer the following question based on the provided context.",
                input_text=f"Question: {query}",
                output_text=response,
                quality_score=5.0,  # Synthetic data is assumed high quality
                source="synthetic"
            )
            
            if self.db.add_training_pair(pair):
                created_count += 1
        
        logger.info(f"Created {created_count} synthetic training pairs")
        return created_count

class ResponseImprover:
    """System for improving responses using training data"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.trainer = RAGTrainer(config)
        
        # Load known good responses for similarity matching
        self.good_responses = self._load_good_responses()
        
    def _load_good_responses(self) -> Dict[str, str]:
        """Load high-quality responses for template matching"""
        
        training_data = self.trainer.db.get_training_data(min_quality=4.0)
        
        good_responses = {}
        for pair in training_data:
            # Create a simple key from the input for matching
            key = pair.input_text.lower().strip()
            good_responses[key] = pair.output_text
        
        return good_responses
    
    def improve_response(self, query: str, current_response: str) -> Tuple[str, float]:
        """Attempt to improve response based on training data"""
        
        query_key = f"Question: {query}".lower().strip()
        
        # Check for exact matches
        if query_key in self.good_responses:
            return self.good_responses[query_key], 1.0
        
        # Check for similar queries (simple keyword matching)
        best_match = None
        best_score = 0.0
        
        for stored_query, stored_response in self.good_responses.items():
            similarity = self._calculate_similarity(query_key, stored_query)
            if similarity > best_score and similarity > 0.8:  # 80% similarity threshold
                best_match = stored_response
                best_score = similarity
        
        if best_match:
            return best_match, best_score
        
        # No improvement found
        return current_response, 0.0
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Simple word-based similarity calculation"""
        
        words1 = set(query1.split())
        words2 = set(query2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0