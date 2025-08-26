#!/usr/bin/env python3
"""Create a new user for the RAG System"""

import sys
import os
import getpass
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.security import SecurityManager
from config.roles import get_valid_roles, get_role_description

def main():
    print("=== RAG System User Creation ===\n")
    
    try:
        # Initialize configuration and security manager
        config = RAGConfig()
        security_manager = SecurityManager(config)
        
        # Get username
        username = input("Enter username: ").strip()
        if not username:
            print("Error: Username cannot be empty")
            return
        
        # Check if user already exists
        existing_users = security_manager.list_users()
        if username in existing_users:
            print(f"Error: User '{username}' already exists")
            return
        
        # Get password
        while True:
            password = getpass.getpass("Enter password: ")
            confirm_password = getpass.getpass("Confirm password: ")
            
            if password != confirm_password:
                print("Error: Passwords do not match. Try again.")
                continue
            
            # Validate password
            is_valid, message = security_manager.validate_password(password)
            if not is_valid:
                print(f"Error: {message}")
                continue
            
            break
        
        # Get role
        valid_roles = get_valid_roles()
        print("\nAvailable roles:")
        for i, role in enumerate(valid_roles, 1):
            print(f"{i}. {role} - {get_role_description(role)}")
        
        while True:
            role_choice = input("\nSelect role (number or name): ").strip()
            
            # Check if it's a number
            if role_choice.isdigit():
                idx = int(role_choice) - 1
                if 0 <= idx < len(valid_roles):
                    role = valid_roles[idx]
                    break
                else:
                    print("Error: Invalid selection. Please try again.")
            # Check if it's a role name
            elif role_choice in valid_roles:
                role = role_choice
                break
            else:
                print(f"Error: Invalid role. Choose from: {', '.join(valid_roles)}")
        
        # Create the user
        try:
            security_manager.create_user(
                username=username,
                password=password,
                role=role
            )
            
            print(f"\n✓ User '{username}' created successfully with role '{role}'")
            print(f"  Access permissions: {get_role_description(role)}")
            
            # Show next steps
            print("\nNext steps:")
            print("1. Use the API login endpoint to authenticate:")
            print(f"   POST http://your-server:8000/api/auth/login")
            print(f"   Body: {{\"username\": \"{username}\", \"password\": \"*****\"}}")
            print("\n2. Use the returned access_token for API requests")
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return
            
    except Exception as e:
        print(f"Error initializing system: {e}")
        print("\nMake sure you have:")
        print("1. Set the JWT_SECRET environment variable")
        print("2. Configured the system properly")
        print("3. Have write access to the data directory")
        return

if __name__ == "__main__":
    main()