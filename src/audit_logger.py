"""Audit logging functionality for RAG system"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import os
from functools import wraps

class AuditLogger:
    def __init__(self, config):
        self.config = config
        self.audit_log_file = Path(config.audit_log_file)
        
        # Ensure audit log directory exists
        self.audit_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup audit logger
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler for audit logs
        file_handler = logging.FileHandler(str(self.audit_log_file))
        file_handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.propagate = False
    
    def log_event(self, event_type: str, user: str, details: Dict[str, Any], 
                  request_ip: Optional[str] = None, user_agent: Optional[str] = None):
        """Log an audit event"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user": user,
            "request_ip": request_ip,
            "user_agent": user_agent,
            "details": details
        }
        
        self.logger.info(json.dumps(audit_entry))
    
    def log_authentication(self, username: str, success: bool, request_ip: str, 
                          user_agent: str, reason: Optional[str] = None):
        """Log authentication attempts"""
        details = {
            "success": success,
            "reason": reason
        }
        
        event_type = "AUTH_SUCCESS" if success else "AUTH_FAILURE"
        self.log_event(event_type, username, details, request_ip, user_agent)
    
    def log_document_access(self, username: str, document_id: str, action: str,
                           request_ip: str, user_agent: str, metadata: Optional[Dict] = None):
        """Log document access events"""
        details = {
            "document_id": document_id,
            "action": action,  # "upload", "query", "download"
            "metadata": metadata or {}
        }
        
        self.log_event("DOCUMENT_ACCESS", username, details, request_ip, user_agent)
    
    def log_admin_action(self, username: str, action: str, target: str,
                        request_ip: str, user_agent: str, details: Optional[Dict] = None):
        """Log administrative actions"""
        audit_details = {
            "action": action,
            "target": target,
            "details": details or {}
        }
        
        self.log_event("ADMIN_ACTION", username, audit_details, request_ip, user_agent)
    
    def log_security_event(self, event_type: str, username: str, request_ip: str,
                          user_agent: str, details: Dict[str, Any]):
        """Log security-related events"""
        self.log_event(f"SECURITY_{event_type}", username, details, request_ip, user_agent)

def audit_endpoint(action: str, target: str = ""):
    """Decorator to automatically audit API endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user info from kwargs
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            
            if request and current_user:
                user_ip = request.client.host
                user_agent = request.headers.get('user-agent', 'Unknown')
                username = current_user.username
                
                # Get audit logger from app state if available
                audit_logger = getattr(request.app.state, 'audit_logger', None)
                
                if audit_logger:
                    # Log the action before execution
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Log successful action
                        audit_logger.log_admin_action(
                            username=username,
                            action=action,
                            target=target,
                            request_ip=user_ip,
                            user_agent=user_agent,
                            details={"status": "success"}
                        )
                        
                        return result
                    except Exception as e:
                        # Log failed action
                        audit_logger.log_admin_action(
                            username=username,
                            action=action,
                            target=target,
                            request_ip=user_ip,
                            user_agent=user_agent,
                            details={"status": "error", "error": str(e)}
                        )
                        raise
                else:
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator