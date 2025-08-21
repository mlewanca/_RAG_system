#!/usr/bin/env python3
"""Setup required directories for RAG system"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig

def setup_directories():
    """Create all required directories with proper permissions"""
    
    print("Setting up RAG system directories...")
    
    # Initialize config
    config = RAGConfig()
    
    # Define directories to create with permissions
    directories = [
        (config.base_dir, 0o755),
        (config.documents_dir, 0o755),
        (f"{config.documents_dir}/service", 0o755),
        (f"{config.documents_dir}/rnd", 0o755),
        (f"{config.documents_dir}/archive", 0o755),
        (f"{config.documents_dir}/quarantine", 0o750),
        (config.chroma_dir, 0o755),
        (config.logs_dir, 0o700),
        (f"{config.base_dir}/backups", 0o755),
        (f"{config.base_dir}/backups/users", 0o700),
        (f"{config.base_dir}/backups/vector_db", 0o755),
        (f"{config.base_dir}/backups/config", 0o700),
        (f"{config.base_dir}/config", 0o700),
        (f"{config.base_dir}/cache", 0o755),
        (f"{config.base_dir}/cache/api_responses", 0o755),
        (f"{config.base_dir}/temp", 0o755),
        (f"{config.base_dir}/temp/cache", 0o755),
        (f"{config.base_dir}/temp/document_processing", 0o755),
        (f"{config.base_dir}/temp/indexing", 0o755),
        (f"{config.base_dir}/monitoring", 0o755),
        (f"{config.base_dir}/security", 0o700),
        (f"{config.base_dir}/audit", 0o700),
        (f"{config.base_dir}/artifacts", 0o755),
    ]
    
    # Create directories
    created = 0
    for dir_path, permissions in directories:
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                # Set permissions on Unix-like systems
                if os.name != 'nt':  # Not Windows
                    os.chmod(path, permissions)
                print(f"✅ Created: {dir_path}")
                created += 1
            except Exception as e:
                print(f"❌ Failed to create {dir_path}: {e}")
        else:
            print(f"✓ Exists: {dir_path}")
    
    # Create log files
    log_files = [
        f"{config.logs_dir}/api.log",
        f"{config.logs_dir}/security.log",
        f"{config.logs_dir}/document_processing.log",
        f"{config.logs_dir}/monitoring.log",
        f"{config.logs_dir}/user_creation.log",
        f"{config.logs_dir}/user_management.log",
        f"{config.logs_dir}/user_audit.log",
    ]
    
    for log_file in log_files:
        path = Path(log_file)
        if not path.exists():
            try:
                path.touch()
                if os.name != 'nt':  # Not Windows
                    os.chmod(path, 0o600)
                print(f"✅ Created log: {log_file}")
            except Exception as e:
                print(f"❌ Failed to create log {log_file}: {e}")
    
    print(f"\n✅ Setup complete! Created {created} new directories.")
    print(f"Base directory: {config.base_dir}")

if __name__ == "__main__":
    setup_directories()