"""Enterprise-grade security implementation for RAG system"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, validator
import secrets
import re
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class UserModel(BaseModel):
    username: str
    email: EmailStr
    role: str
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    password_changed_at: datetime
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class SecurityManager:
    def __init__(self, config):
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.jwt_secret = config.jwt_secret
        self.jwt_algorithm = config.jwt_algorithm
        self.token_expire_hours = config.token_expire_hours
        self.users_db_path = Path(config.base_dir) / "config" / "users.json"
        self._ensure_users_db()
    
    def _ensure_users_db(self):
        """Ensure users database exists"""
        if not self.users_db_path.exists():
            self.users_db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.users_db_path, 'w') as f:
                json.dump({}, f)
            self.users_db_path.chmod(0o600)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)
    
    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Validate password meets security requirements"""
        if len(password) < self.config.password_min_length:
            return False, f"Password must be at least {self.config.password_min_length} characters long"
        
        checks = [
            (self.config.password_require_uppercase, r'[A-Z]', "uppercase letter"),
            (self.config.password_require_lowercase, r'[a-z]', "lowercase letter"),
            (self.config.password_require_numbers, r'\d', "number"),
            (self.config.password_require_special, r'[!@#$%^&*(),.?":{}|<>]', "special character")
        ]
        
        for required, pattern, name in checks:
            if required and not re.search(pattern, password):
                return False, f"Password must contain at least one {name}"
        
        return True, "Password meets requirements"
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify JWT token and extract data"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            username: str = payload.get("sub")
            role: str = payload.get("role")
            if username is None:
                return None
            return TokenData(username=username, role=role)
        except JWTError:
            return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user from database"""
        try:
            with open(self.users_db_path, 'r') as f:
                users = json.load(f)
            return users.get(username)
        except Exception as e:
            logger.error(f"Error reading users database: {e}")
            return None
    
    def save_user(self, username: str, user_data: Dict):
        """Save user to database"""
        try:
            with open(self.users_db_path, 'r') as f:
                users = json.load(f)
            
            users[username] = user_data
            
            with open(self.users_db_path, 'w') as f:
                json.dump(users, f, indent=2, default=str)
            
            self.users_db_path.chmod(0o600)
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        user = self.get_user(username)
        if not user:
            return None
        
        # Check if account is locked
        if user.get('locked_until'):
            locked_until = datetime.fromisoformat(user['locked_until'])
            if datetime.utcnow() < locked_until:
                return None
        
        # Verify password
        if not self.verify_password(password, user['hashed_password']):
            # Increment failed attempts
            user['failed_attempts'] = user.get('failed_attempts', 0) + 1
            
            # Lock account if too many failed attempts
            if user['failed_attempts'] >= self.config.max_login_attempts:
                user['locked_until'] = (datetime.utcnow() + 
                                      timedelta(minutes=self.config.lockout_duration_minutes)).isoformat()
            
            self.save_user(username, user)
            return None
        
        # Reset failed attempts on successful login
        user['failed_attempts'] = 0
        user['locked_until'] = None
        user['last_login'] = datetime.utcnow().isoformat()
        self.save_user(username, user)
        
        return user
    
    def check_password_age(self, username: str) -> bool:
        """Check if password needs to be changed"""
        user = self.get_user(username)
        if not user:
            return False
        
        password_changed = datetime.fromisoformat(user.get('password_changed_at', 
                                                          user.get('created_at')))
        age_days = (datetime.utcnow() - password_changed).days
        
        return age_days > self.config.password_max_age_days
    
    def generate_secure_password(self, length: int = 16) -> str:
        """Generate a secure random password"""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password