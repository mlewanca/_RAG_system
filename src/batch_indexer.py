"""Batch document indexing with fault tolerance"""

import sys
from pathlib import Path
import argparse
import json
from datetime import datetime
import time
from typing import List, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.document_processor import DocumentProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchIndexer:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.processor = DocumentProcessor(config)
        self.progress_file = Path(config.base_dir) / "temp" / "indexing" / "progress.json"
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> List[Path]:
        """Scan directory for processable documents"""
        supported_extensions = list(self.processor.file_loaders.keys())
        documents = []
        
        if recursive:
            for ext in supported_extensions:
                documents.extend(directory.rglob(f"*{ext}"))
        else:
            for ext in supported_extensions:
                documents.extend(directory.glob(f"*{ext}"))
        
        return sorted(documents)
    
    def load_progress(self) -> Dict:
        """Load indexing progress from file"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        
        return {
            "processed": [],
            "failed": [],
            "skipped": [],
            "start_time": datetime.utcnow().isoformat()
        }
    
    def save_progress(self, progress: Dict):
        """Save indexing progress to file"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
    def index_batch(
        self,
        file_paths: List[Path],
        max_workers: int = 4,
        resume: bool = True,
        dry_run: bool = False
    ) -> Dict[str, List[str]]:
        """Index a batch of documents"""
        
        # Load progress if resuming
        progress = self.load_progress() if resume else {
            "processed": [],
            "failed": [],
            "skipped": [],
            "start_time": datetime.utcnow().isoformat()
        }
        
        # Filter out already processed files
        if resume:
            processed_set = set(progress["processed"])
            file_paths = [f for f in file_paths if str(f) not in processed_set]
            
            if not file_paths:
                logger.info("All files already processed")
                return progress
        
        logger.info(f"Starting batch indexing of {len(file_paths)} files")
        
        if dry_run:
            logger.info("DRY RUN - No files will be processed")
            for path in file_paths:
                print(f"Would process: {path}")
            return progress
        
        # Process files
        start_time = time.time()
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_file, path): path 
                for path in file_paths
            }
            
            # Process results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                
                try:
                    result = future.result()
                    
                    if result["status"] == "success":
                        progress["processed"].append(str(path))
                        processed_count += 1
                        logger.info(f"✅ Processed: {path.name}")
                    elif result["status"] == "duplicate":
                        progress["skipped"].append(str(path))
                        logger.info(f"⏭️  Skipped (duplicate): {path.name}")
                    else:
                        progress["failed"].append({
                            "path": str(path),
                            "error": result.get("message", "Unknown error"),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        logger.error(f"❌ Failed: {path.name} - {result.get('message')}")
                
                except Exception as e:
                    progress["failed"].append({
                        "path": str(path),
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    logger.error(f"❌ Failed: {path.name} - {e}")
                
                # Save progress periodically
                if processed_count % 10 == 0:
                    self.save_progress(progress)
        
        # Final save
        progress["end_time"] = datetime.utcnow().isoformat()
        progress["duration_seconds"] = time.time() - start_time
        self.save_progress(progress)
        
        # Print summary
        self._print_summary(progress)
        
        return progress
    
    def _process_single_file(self, file_path: Path) -> Dict:
        """Process a single file with error handling"""
        try:
            return self.processor.process_document(str(file_path))
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _print_summary(self, progress: Dict):
        """Print indexing summary"""
        print("\n" + "="*50)
        print("BATCH INDEXING SUMMARY")
        print("="*50)
        print(f"Total processed: {len(progress['processed'])}")
        print(f"Skipped (duplicates): {len(progress['skipped'])}")
        print(f"Failed: {len(progress['failed'])}")
        
        if "duration_seconds" in progress:
            duration = progress["duration_seconds"]
            print(f"Duration: {duration:.2f} seconds")
            
            total_files = len(progress['processed']) + len(progress['skipped']) + len(progress['failed'])
            if total_files > 0:
                print(f"Average time per file: {duration/total_files:.2f} seconds")
        
        if progress['failed']:
            print("\nFailed files:")
            for failure in progress['failed'][:10]:  # Show first 10 failures
                print(f"  - {Path(failure['path']).name}: {failure['error']}")
            
            if len(progress['failed']) > 10:
                print(f"  ... and {len(progress['failed']) - 10} more")
    
    def retry_failed(self, max_workers: int = 4) -> Dict:
        """Retry processing of failed files"""
        progress = self.load_progress()
        
        if not progress.get('failed'):
            logger.info("No failed files to retry")
            return progress
        
        failed_paths = [Path(f['path']) for f in progress['failed']]
        logger.info(f"Retrying {len(failed_paths)} failed files")
        
        # Clear failed list for retry
        progress['failed'] = []
        self.save_progress(progress)
        
        # Retry processing
        return self.index_batch(failed_paths, max_workers=max_workers, resume=True)

def main():
    parser = argparse.ArgumentParser(description="Batch document indexer for RAG system")
    parser.add_argument("path", help="Directory or file to index")
    parser.add_argument("--recursive", "-r", action="store_true", 
                       help="Recursively index subdirectories")
    parser.add_argument("--workers", "-w", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    parser.add_argument("--no-resume", action="store_true",
                       help="Start fresh, ignoring previous progress")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be indexed without processing")
    parser.add_argument("--retry-failed", action="store_true",
                       help="Retry previously failed files")
    
    args = parser.parse_args()
    
    # Initialize
    config = RAGConfig()
    indexer = BatchIndexer(config)
    
    if args.retry_failed:
        # Retry failed files
        indexer.retry_failed(max_workers=args.workers)
    else:
        # Normal indexing
        path = Path(args.path)
        
        if not path.exists():
            print(f"Error: Path does not exist: {path}")
            sys.exit(1)
        
        if path.is_file():
            # Index single file
            files = [path]
        else:
            # Scan directory
            files = indexer.scan_directory(path, recursive=args.recursive)
            
            if not files:
                print(f"No supported documents found in {path}")
                sys.exit(0)
            
            print(f"Found {len(files)} documents to index")
        
        # Run indexing
        indexer.index_batch(
            files,
            max_workers=args.workers,
            resume=not args.no_resume,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()