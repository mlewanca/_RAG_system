#!/usr/bin/env python3
"""
Example API client for RAG System

This demonstrates how to interact with the RAG System API including:
- Authentication
- Document queries
- Error handling
- Rate limiting
"""

import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime

class RAGClient:
    """Client for interacting with RAG System API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.session = requests.Session()
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate and obtain access token"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password}
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data["access_token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
            print(f"✅ Logged in as {username}")
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ Login failed: {e.response.json()}")
            return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def query(self, query: str, max_results: int = 5, 
              filters: Optional[Dict] = None) -> Optional[Dict]:
        """Query documents"""
        if not self.token:
            print("❌ Not authenticated. Please login first.")
            return None
        
        try:
            payload = {
                "query": query,
                "max_results": max_results
            }
            if filters:
                payload["filters"] = filters
            
            response = self.session.post(
                f"{self.base_url}/api/query",
                json=payload
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("⚠️  Rate limit exceeded. Waiting before retry...")
                time.sleep(60)  # Wait 1 minute
                return self.query(query, max_results, filters)
            else:
                print(f"❌ Query failed: {e.response.json()}")
                return None
        except Exception as e:
            print(f"❌ Query error: {e}")
            return None
    
    def get_profile(self) -> Optional[Dict]:
        """Get current user profile"""
        if not self.token:
            print("❌ Not authenticated. Please login first.")
            return None
        
        try:
            response = self.session.get(f"{self.base_url}/api/user/profile")
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ Failed to get profile: {e.response.json()}")
            return None
        except Exception as e:
            print(f"❌ Profile error: {e}")
            return None
    
    def upload_document(self, file_path: str) -> Optional[Dict]:
        """Upload a document (admin only)"""
        if not self.token:
            print("❌ Not authenticated. Please login first.")
            return None
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/documents/upload",
                json={"file_path": file_path}
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print("❌ Forbidden: Admin access required")
            else:
                print(f"❌ Upload failed: {e.response.json()}")
            return None
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            print(f"✅ API is {data['status']} at {data['timestamp']}")
            return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

def format_results(results: List[Dict]) -> None:
    """Pretty print query results"""
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Score: {result.get('score', 'N/A')}")
        
        metadata = result.get('metadata', {})
        if metadata.get('type') == 'generated':
            print(f"Type: AI Generated Response")
            print(f"Model: {metadata.get('model', 'Unknown')}")
        else:
            print(f"Source: {metadata.get('filename', 'Unknown')}")
            print(f"Category: {metadata.get('category', 'Unknown')}")
        
        content = result.get('content', '')
        if len(content) > 500:
            content = content[:500] + "..."
        print(f"\nContent:\n{content}")

def main():
    """Example usage of RAG Client"""
    
    # Initialize client
    client = RAGClient("http://localhost:8000")
    
    # Check health
    if not client.health_check():
        return
    
    # Login
    username = input("Username: ")
    password = input("Password: ")
    
    if not client.login(username, password):
        return
    
    # Get user profile
    profile = client.get_profile()
    if profile:
        print(f"\n👤 User Profile:")
        print(f"  - Username: {profile['username']}")
        print(f"  - Role: {profile['role']}")
        print(f"  - Email: {profile['email']}")
    
    # Interactive query loop
    print("\n🔍 RAG Query Interface (type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        query = input("\nEnter your query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        # Perform query
        print(f"\n⏳ Searching for: '{query}'...")
        start_time = time.time()
        
        response = client.query(query, max_results=3)
        
        if response:
            elapsed_time = time.time() - start_time
            print(f"\n✅ Found {len(response['results'])} results in {elapsed_time:.2f}s")
            
            format_results(response['results'])
            
            # Show processing time
            print(f"\n⏱️  Total processing time: {response['processing_time']:.3f}s")
        
        # Ask if user wants to refine search
        refine = input("\nRefine search with filters? (y/n): ").lower()
        if refine == 'y':
            category = input("Category (service/rnd/archive): ").strip()
            if category:
                print(f"\n⏳ Searching with category filter: {category}")
                filtered_response = client.query(
                    query, 
                    max_results=3,
                    filters={"category": category}
                )
                if filtered_response:
                    format_results(filtered_response['results'])
    
    print("\n👋 Thank you for using RAG System!")

if __name__ == "__main__":
    main()