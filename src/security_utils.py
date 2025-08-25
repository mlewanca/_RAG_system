"""Security utilities and hardening functions for RAG system"""

import secrets
import string
import re
import os
from typing import Optional, Tuple, List
import hashlib
import hmac
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_secure_password(
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_special: bool = True
    ) -> str:
        """Generate a secure random password"""
        characters = ""
        
        if include_uppercase:
            characters += string.ascii_uppercase
        if include_lowercase:
            characters += string.ascii_lowercase
        if include_digits:
            characters += string.digits
        if include_special:
            characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        if not characters:
            raise ValueError("At least one character type must be included")
        
        # Ensure password has at least one of each required type
        password = []
        if include_uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if include_lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if include_digits:
            password.append(secrets.choice(string.digits))
        if include_special:
            password.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
        
        # Fill the rest randomly
        for _ in range(length - len(password)):
            password.append(secrets.choice(characters))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not text:
            return ""
        
        # Truncate to max length
        text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if char in '\n\t' or ord(char) >= 32)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        if not filename:
            return "unnamed"
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 100:
            name = name[:100]
        
        return name + ext
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def hash_data(data: str, salt: Optional[str] = None) -> str:
        """Create a secure hash of data"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 for secure hashing
        dk = hashlib.pbkdf2_hmac('sha256', 
                                data.encode('utf-8'), 
                                salt.encode('utf-8'), 
                                100000)  # iterations
        
        return f"{salt}${dk.hex()}"
    
    @staticmethod
    def verify_hash(data: str, hash_string: str) -> bool:
        """Verify data against hash"""
        try:
            salt, hash_hex = hash_string.split('$')
            test_hash = SecurityUtils.hash_data(data, salt)
            return hmac.compare_digest(test_hash, hash_string)
        except Exception:
            return False
    
    @staticmethod
    def is_safe_url(url: str, allowed_hosts: List[str]) -> bool:
        """Check if URL is safe for redirect"""
        from urllib.parse import urlparse
        
        try:
            result = urlparse(url)
            # Check if URL is relative
            if not result.netloc:
                return True
            # Check if host is allowed
            return result.netloc in allowed_hosts
        except Exception:
            return False
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
        """Mask sensitive data for logging"""
        if not data or len(data) <= visible_chars:
            return mask_char * 8
        
        if len(data) <= visible_chars * 2:
            # Too short to show beginning and end
            return data[:visible_chars] + mask_char * (len(data) - visible_chars)
        
        # Show beginning and end
        masked_length = len(data) - (visible_chars * 2)
        return data[:visible_chars] + mask_char * masked_length + data[-visible_chars:]
    
    @staticmethod
    def rate_limit_key(identifier: str, window: int = 60) -> str:
        """Generate rate limit key for caching"""
        current_window = int(datetime.utcnow().timestamp() / window)
        return f"rate_limit:{identifier}:{current_window}"
    
    @staticmethod
    def validate_jwt_claims(claims: dict) -> Tuple[bool, Optional[str]]:
        """Validate JWT claims"""
        # Check expiration
        if 'exp' in claims:
            if datetime.fromtimestamp(claims['exp']) < datetime.utcnow():
                return False, "Token has expired"
        
        # Check not before
        if 'nbf' in claims:
            if datetime.fromtimestamp(claims['nbf']) > datetime.utcnow():
                return False, "Token not yet valid"
        
        # Check required claims
        required_claims = ['sub', 'role']
        for claim in required_claims:
            if claim not in claims:
                return False, f"Missing required claim: {claim}"
        
        return True, None

# Content Security Policy header
CSP_HEADER = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "https:"],
    "font-src": ["'self'"],
    "connect-src": ["'self'"],
    "frame-ancestors": ["'none'"],
    "form-action": ["'self'"],
    "base-uri": ["'self'"]
}

def generate_csp_header() -> str:
    """Generate Content Security Policy header"""
    policies = []
    for directive, sources in CSP_HEADER.items():
        policies.append(f"{directive} {' '.join(sources)}")
    return "; ".join(policies)

# Security headers to add to all responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": generate_csp_header()
}