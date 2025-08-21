"""Interactive user creation script for RAG system"""

import sys
from pathlib import Path
from datetime import datetime
import getpass
import json
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.security import SecurityManager

def create_user_interactive(security_manager: SecurityManager):
    """Interactive user creation"""
    print("\n=== RAG System User Creation ===\n")
    
    # Get username
    while True:
        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty")
            continue
        if security_manager.get_user(username):
            print(f"User '{username}' already exists")
            continue
        break
    
    # Get email
    while True:
        email = input("Email: ").strip()
        if not email or '@' not in email:
            print("Please enter a valid email address")
            continue
        break
    
    # Get full name
    full_name = input("Full name (optional): ").strip()
    
    # Get role
    print("\nAvailable roles:")
    print("  1. admin - Full system access")
    print("  2. developer - Access to service and R&D documents")
    print("  3. service - Access to service documents only")
    
    while True:
        role_choice = input("\nSelect role (1-3): ").strip()
        role_map = {"1": "admin", "2": "developer", "3": "service"}
        if role_choice in role_map:
            role = role_map[role_choice]
            break
        print("Invalid choice. Please select 1, 2, or 3")
    
    # Get password
    while True:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("Passwords do not match")
            continue
        
        valid, message = security_manager.validate_password_strength(password)
        if not valid:
            print(f"Password validation failed: {message}")
            continue
        
        break
    
    # Create user
    try:
        user_data = {
            "username": username,
            "email": email,
            "role": role,
            "full_name": full_name if full_name else None,
            "hashed_password": security_manager.get_password_hash(password),
            "created_at": datetime.utcnow().isoformat(),
            "password_changed_at": datetime.utcnow().isoformat(),
            "disabled": False,
            "failed_attempts": 0,
            "locked_until": None
        }
        
        security_manager.save_user(username, user_data)
        
        print(f"\n✅ User '{username}' created successfully!")
        print(f"   Role: {role}")
        print(f"   Email: {email}")
        
        # Log user creation
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "user_created",
            "username": username,
            "role": role,
            "created_by": "create_user_script"
        }
        
        log_file = Path(security_manager.config.logs_dir) / "user_creation.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
        
    except Exception as e:
        print(f"\n❌ Error creating user: {e}")
        return False
    
    return True

def create_user_batch(security_manager: SecurityManager, username: str, email: str, 
                     role: str, password: str, full_name: str = None):
    """Create user in batch mode"""
    try:
        # Validate inputs
        if security_manager.get_user(username):
            raise ValueError(f"User '{username}' already exists")
        
        if role not in ["admin", "developer", "service"]:
            raise ValueError(f"Invalid role: {role}")
        
        valid, message = security_manager.validate_password_strength(password)
        if not valid:
            raise ValueError(f"Password validation failed: {message}")
        
        # Create user
        user_data = {
            "username": username,
            "email": email,
            "role": role,
            "full_name": full_name,
            "hashed_password": security_manager.get_password_hash(password),
            "created_at": datetime.utcnow().isoformat(),
            "password_changed_at": datetime.utcnow().isoformat(),
            "disabled": False,
            "failed_attempts": 0,
            "locked_until": None
        }
        
        security_manager.save_user(username, user_data)
        
        print(f"✅ User '{username}' created successfully")
        
        # Log user creation
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "user_created",
            "username": username,
            "role": role,
            "created_by": "create_user_script_batch"
        }
        
        log_file = Path(security_manager.config.logs_dir) / "user_creation.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating user '{username}': {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create users for RAG system")
    parser.add_argument("--batch", action="store_true", help="Batch mode")
    parser.add_argument("--username", help="Username (batch mode)")
    parser.add_argument("--email", help="Email (batch mode)")
    parser.add_argument("--role", choices=["admin", "developer", "service"], 
                       help="User role (batch mode)")
    parser.add_argument("--password", help="Password (batch mode)")
    parser.add_argument("--full-name", help="Full name (batch mode)")
    
    args = parser.parse_args()
    
    # Initialize configuration and security manager
    config = RAGConfig()
    security_manager = SecurityManager(config)
    
    if args.batch:
        # Batch mode
        if not all([args.username, args.email, args.role, args.password]):
            print("Error: Batch mode requires --username, --email, --role, and --password")
            sys.exit(1)
        
        success = create_user_batch(
            security_manager,
            args.username,
            args.email,
            args.role,
            args.password,
            args.full_name
        )
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        try:
            while True:
                success = create_user_interactive(security_manager)
                if not success:
                    sys.exit(1)
                
                another = input("\nCreate another user? (y/n): ").strip().lower()
                if another != 'y':
                    break
        except KeyboardInterrupt:
            print("\n\nUser creation cancelled")
            sys.exit(0)

if __name__ == "__main__":
    main()