"""Enhanced document processor with multimodal support"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import json
from datetime import datetime
import shutil
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed

# Document processing libraries
from langchain.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    UnstructuredImageLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, config):
        self.config = config
        self.documents_dir = Path(config.documents_dir)
        self.quarantine_dir = Path(config.quarantine_dir)
        self.chroma_dir = Path(config.chroma_dir)
        
        # Ensure directories exist
        for dir_path in [self.documents_dir, self.quarantine_dir, self.chroma_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(
            model=config.embedding_model,
            base_url="http://localhost:11434"
        )
        
        # Initialize vector store
        self.client = chromadb.PersistentClient(path=str(self.chroma_dir))
        self.collection_name = "rag_documents"
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Supported file types
        self.file_loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.md': UnstructuredMarkdownLoader,
            '.docx': UnstructuredWordDocumentLoader,
            '.doc': UnstructuredWordDocumentLoader,
            '.xlsx': UnstructuredExcelLoader,
            '.xls': UnstructuredExcelLoader,
            '.png': UnstructuredImageLoader,
            '.jpg': UnstructuredImageLoader,
            '.jpeg': UnstructuredImageLoader
        }
        
        logger.info("Document processor initialized")
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def is_duplicate(self, file_hash: str) -> bool:
        """Check if document already exists in the system"""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            results = collection.get(
                where={"file_hash": file_hash},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception as e:
            logger.error(f"Error checking for duplicate: {e}")
            return False
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file"""
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        metadata = {
            "filename": file_path.name,
            "file_path": str(file_path),
            "file_size": stat.st_size,
            "mime_type": mime_type,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "processed_at": datetime.utcnow().isoformat(),
            "file_hash": self.get_file_hash(file_path)
        }
        
        return metadata
    
    def load_document(self, file_path: Path) -> Optional[List[Any]]:
        """Load document using appropriate loader"""
        file_extension = file_path.suffix.lower()
        
        if file_extension not in self.file_loaders:
            logger.warning(f"Unsupported file type: {file_extension}")
            return None
        
        try:
            loader_class = self.file_loaders[file_extension]
            loader = loader_class(str(file_path))
            documents = loader.load()
            
            logger.info(f"Successfully loaded {file_path.name} with {len(documents)} pages/sections")
            return documents
        
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
            return None
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a single document"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Processing document: {file_path.name}")
        
        try:
            # Extract metadata
            metadata = self.extract_metadata(file_path)
            
            # Check for duplicates
            if self.is_duplicate(metadata['file_hash']):
                logger.info(f"Document already exists: {file_path.name}")
                return {
                    "status": "duplicate",
                    "message": "Document already processed",
                    "file_hash": metadata['file_hash']
                }
            
            # Load document
            documents = self.load_document(file_path)
            if not documents:
                raise ValueError("Failed to load document")
            
            # Split into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split {file_path.name} into {len(chunks)} chunks")
            
            # Add metadata to chunks
            for chunk in chunks:
                chunk.metadata.update(metadata)
            
            # Store in vector database
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Generate embeddings and store
            texts = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            
            # Generate unique IDs for chunks
            ids = [f"{metadata['file_hash']}_{i}" for i in range(len(chunks))]
            
            # Batch process embeddings
            embeddings = self.embeddings.embed_documents(texts)
            
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            # Copy to appropriate directory
            category_dir = self.documents_dir / "service"  # Default category
            category_dir.mkdir(exist_ok=True)
            destination = category_dir / file_path.name
            shutil.copy2(file_path, destination)
            
            logger.info(f"Successfully processed: {file_path.name}")
            
            return {
                "status": "success",
                "message": "Document processed successfully",
                "document_id": metadata['file_hash'],
                "chunks": len(chunks),
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            
            # Move to quarantine
            quarantine_path = self.quarantine_dir / file_path.name
            shutil.move(str(file_path), str(quarantine_path))
            
            return {
                "status": "error",
                "message": str(e),
                "quarantined": True
            }
    
    def batch_process(self, file_paths: List[str], max_workers: int = 4) -> List[Dict[str, Any]]:
        """Process multiple documents in parallel"""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.process_document, path): path 
                for path in file_paths
            }
            
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {path}: {e}")
                    results.append({
                        "status": "error",
                        "file": path,
                        "message": str(e)
                    })
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            
            # Get collection info
            count = collection.count()
            
            # Count documents by type
            all_docs = collection.get(limit=count)
            
            doc_types = {}
            unique_files = set()
            
            for metadata in all_docs.get('metadatas', []):
                if metadata:
                    mime_type = metadata.get('mime_type', 'unknown')
                    doc_types[mime_type] = doc_types.get(mime_type, 0) + 1
                    unique_files.add(metadata.get('file_hash'))
            
            return {
                "total_chunks": count,
                "unique_documents": len(unique_files),
                "document_types": doc_types,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}