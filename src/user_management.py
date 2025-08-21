"""Comprehensive user management for RAG system"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import argparse
from typing import List, Dict, Optional
from tabulate import tabulate

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.security import SecurityManager

class UserManager:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.security_manager = SecurityManager(config)
        self.users_db_path = Path(config.base_dir) / "config" / "users.json"
    
    def list_users(self, show_details: bool = False) -> List[Dict]:
        """List all users"""
        try:
            with open(self.users_db_path, 'r') as f:
                users = json.load(f)
            
            user_list = []
            for username, user_data in users.items():
                user_info = {
                    "username": username,
                    "email": user_data.get("email", ""),
                    "role": user_data.get("role", ""),
                    "created": user_data.get("created_at", "")[:10],
                    "status": "locked" if user_data.get("locked_until") else 
                             ("disabled" if user_data.get("disabled") else "active")
                }
                
                if show_details:
                    user_info.update({
                        "full_name": user_data.get("full_name", ""),
                        "last_login": user_data.get("last_login", "N/A"),
                        "failed_attempts": user_data.get("failed_attempts", 0),
                        "password_age": self._calculate_password_age(user_data)
                    })
                
                user_list.append(user_info)
            
            return sorted(user_list, key=lambda x: x["username"])
            
        except Exception as e:
            print(f"Error listing users: {e}")
            return []
    
    def _calculate_password_age(self, user_data: Dict) -> int:
        """Calculate password age in days"""
        password_changed = user_data.get("password_changed_at", user_data.get("created_at"))
        if password_changed:
            changed_date = datetime.fromisoformat(password_changed)
            return (datetime.utcnow() - changed_date).days
        return 0
    
    def enable_user(self, username: str) -> bool:
        """Enable a disabled user"""
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return False
        
        user["disabled"] = False
        self.security_manager.save_user(username, user)
        
        self._log_action("user_enabled", username)
        print(f"✅ User '{username}' enabled")
        return True
    
    def disable_user(self, username: str) -> bool:
        """Disable a user"""
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return False
        
        user["disabled"] = True
        self.security_manager.save_user(username, user)
        
        self._log_action("user_disabled", username)
        print(f"✅ User '{username}' disabled")
        return True
    
    def unlock_user(self, username: str) -> bool:
        """Unlock a locked user account"""
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return False
        
        user["locked_until"] = None
        user["failed_attempts"] = 0
        self.security_manager.save_user(username, user)
        
        self._log_action("user_unlocked", username)
        print(f"✅ User '{username}' unlocked")
        return True
    
    def change_role(self, username: str, new_role: str) -> bool:
        """Change user role"""
        if new_role not in ["admin", "developer", "service"]:
            print(f"Invalid role: {new_role}")
            return False
        
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return False
        
        old_role = user.get("role")
        user["role"] = new_role
        self.security_manager.save_user(username, user)
        
        self._log_action("role_changed", username, {
            "old_role": old_role,
            "new_role": new_role
        })
        print(f"✅ Changed role for '{username}' from {old_role} to {new_role}")
        return True
    
    def delete_user(self, username: str, confirm: bool = False) -> bool:
        """Delete a user"""
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return False
        
        if not confirm:
            response = input(f"Are you sure you want to delete user '{username}'? (yes/no): ")
            if response.lower() != "yes":
                print("Deletion cancelled")
                return False
        
        try:
            with open(self.users_db_path, 'r') as f:
                users = json.load(f)
            
            del users[username]
            
            with open(self.users_db_path, 'w') as f:
                json.dump(users, f, indent=2)
            
            self._log_action("user_deleted", username)
            print(f"✅ User '{username}' deleted")
            return True
            
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def update_user_info(self, username: str, email: str = None, full_name: str = None) -> bool:
        """Update user information"""
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return False
        
        updates = {}
        if email:
            user["email"] = email
            updates["email"] = email
        
        if full_name is not None:
            user["full_name"] = full_name if full_name else None
            updates["full_name"] = full_name
        
        if updates:
            self.security_manager.save_user(username, user)
            self._log_action("user_info_updated", username, updates)
            print(f"✅ Updated information for user '{username}'")
            return True
        
        print("No updates provided")
        return False
    
    def show_user_details(self, username: str):
        """Show detailed user information"""
        user = self.security_manager.get_user(username)
        if not user:
            print(f"User '{username}' not found")
            return
        
        print(f"\n=== User Details: {username} ===")
        print(f"Email: {user.get('email', 'N/A')}")
        print(f"Full Name: {user.get('full_name', 'N/A')}")
        print(f"Role: {user.get('role', 'N/A')}")
        print(f"Created: {user.get('created_at', 'N/A')}")
        print(f"Last Login: {user.get('last_login', 'Never')}")
        print(f"Status: {'Disabled' if user.get('disabled') else 'Active'}")
        print(f"Failed Login Attempts: {user.get('failed_attempts', 0)}")
        
        if user.get('locked_until'):
            print(f"Locked Until: {user.get('locked_until')}")
        
        password_age = self._calculate_password_age(user)
        print(f"Password Age: {password_age} days")
        
        if password_age > self.config.password_max_age_days:
            print("⚠️  Password expired - needs to be changed")
    
    def get_expired_passwords(self) -> List[str]:
        """Get list of users with expired passwords"""
        expired_users = []
        
        try:
            with open(self.users_db_path, 'r') as f:
                users = json.load(f)
            
            for username, user_data in users.items():
                if user_data.get("disabled"):
                    continue
                
                password_age = self._calculate_password_age(user_data)
                if password_age > self.config.password_max_age_days:
                    expired_users.append(username)
            
            return expired_users
            
        except Exception as e:
            print(f"Error checking expired passwords: {e}")
            return []
    
    def _log_action(self, action: str, username: str, details: Dict = None):
        """Log management action"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "username": username,
            "performed_by": "user_management_script"
        }
        
        if details:
            log_entry["details"] = details
        
        log_file = Path(self.config.logs_dir) / "user_management.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

def main():
    parser = argparse.ArgumentParser(description="User management for RAG system")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List users
    list_parser = subparsers.add_parser("list", help="List all users")
    list_parser.add_argument("--details", action="store_true", help="Show detailed information")
    
    # Show user
    show_parser = subparsers.add_parser("show", help="Show user details")
    show_parser.add_argument("username", help="Username to show")
    
    # Enable user
    enable_parser = subparsers.add_parser("enable", help="Enable a user")
    enable_parser.add_argument("username", help="Username to enable")
    
    # Disable user
    disable_parser = subparsers.add_parser("disable", help="Disable a user")
    disable_parser.add_argument("username", help="Username to disable")
    
    # Unlock user
    unlock_parser = subparsers.add_parser("unlock", help="Unlock a user")
    unlock_parser.add_argument("username", help="Username to unlock")
    
    # Change role
    role_parser = subparsers.add_parser("change-role", help="Change user role")
    role_parser.add_argument("username", help="Username")
    role_parser.add_argument("role", choices=["admin", "developer", "service"], help="New role")
    
    # Update user
    update_parser = subparsers.add_parser("update", help="Update user information")
    update_parser.add_argument("username", help="Username to update")
    update_parser.add_argument("--email", help="New email address")
    update_parser.add_argument("--full-name", help="New full name")
    
    # Delete user
    delete_parser = subparsers.add_parser("delete", help="Delete a user")
    delete_parser.add_argument("username", help="Username to delete")
    delete_parser.add_argument("--confirm", action="store_true", help="Skip confirmation")
    
    # Check expired
    expired_parser = subparsers.add_parser("check-expired", help="Check for expired passwords")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize
    config = RAGConfig()
    manager = UserManager(config)
    
    # Execute command
    if args.command == "list":
        users = manager.list_users(show_details=args.details)
        if users:
            headers = list(users[0].keys())
            rows = [list(user.values()) for user in users]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        else:
            print("No users found")
    
    elif args.command == "show":
        manager.show_user_details(args.username)
    
    elif args.command == "enable":
        manager.enable_user(args.username)
    
    elif args.command == "disable":
        manager.disable_user(args.username)
    
    elif args.command == "unlock":
        manager.unlock_user(args.username)
    
    elif args.command == "change-role":
        manager.change_role(args.username, args.role)
    
    elif args.command == "update":
        manager.update_user_info(args.username, args.email, args.full_name)
    
    elif args.command == "delete":
        manager.delete_user(args.username, args.confirm)
    
    elif args.command == "check-expired":
        expired = manager.get_expired_passwords()
        if expired:
            print("Users with expired passwords:")
            for username in expired:
                print(f"  - {username}")
        else:
            print("No users have expired passwords")

if __name__ == "__main__":
    main()