"""Tests for security module"""

import pytest
from datetime import datetime, timedelta
import json

def test_password_hashing(security_manager):
    """Test password hashing and verification"""
    password = "TestPassword123!"
    hashed = security_manager.get_password_hash(password)
    
    assert hashed != password
    assert security_manager.verify_password(password, hashed)
    assert not security_manager.verify_password("WrongPassword", hashed)

def test_password_validation(security_manager):
    """Test password strength validation"""
    # Valid password
    valid, msg = security_manager.validate_password_strength("ValidPass123!")
    assert valid
    
    # Too short
    valid, msg = security_manager.validate_password_strength("Short1!")
    assert not valid
    assert "at least" in msg
    
    # Missing uppercase
    valid, msg = security_manager.validate_password_strength("lowercase123!")
    assert not valid
    assert "uppercase" in msg
    
    # Missing lowercase
    valid, msg = security_manager.validate_password_strength("UPPERCASE123!")
    assert not valid
    assert "lowercase" in msg
    
    # Missing number
    valid, msg = security_manager.validate_password_strength("NoNumbers!abc")
    assert not valid
    assert "number" in msg
    
    # Missing special character
    valid, msg = security_manager.validate_password_strength("NoSpecial123")
    assert not valid
    assert "special" in msg

def test_token_creation_and_verification(security_manager):
    """Test JWT token creation and verification"""
    data = {"sub": "testuser", "role": "developer"}
    token = security_manager.create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    # Verify token
    token_data = security_manager.verify_token(token)
    assert token_data is not None
    assert token_data.username == "testuser"
    assert token_data.role == "developer"
    
    # Test invalid token
    invalid_token_data = security_manager.verify_token("invalid.token.here")
    assert invalid_token_data is None

def test_token_expiration(security_manager):
    """Test token expiration"""
    data = {"sub": "testuser", "role": "developer"}
    # Create token with short expiration
    token = security_manager.create_access_token(data, expires_delta=timedelta(seconds=-1))
    
    # Token should be expired
    token_data = security_manager.verify_token(token)
    assert token_data is None

def test_user_management(security_manager, sample_user):
    """Test user creation and retrieval"""
    # Create user
    user_data = {
        "username": sample_user["username"],
        "email": sample_user["email"],
        "role": sample_user["role"],
        "hashed_password": security_manager.get_password_hash(sample_user["password"]),
        "created_at": datetime.utcnow().isoformat(),
        "disabled": False
    }
    
    security_manager.save_user(sample_user["username"], user_data)
    
    # Retrieve user
    retrieved_user = security_manager.get_user(sample_user["username"])
    assert retrieved_user is not None
    assert retrieved_user["email"] == sample_user["email"]
    assert retrieved_user["role"] == sample_user["role"]
    
    # Test non-existent user
    non_existent = security_manager.get_user("nonexistent")
    assert non_existent is None

def test_authentication(security_manager, sample_user):
    """Test user authentication"""
    # Create user
    user_data = {
        "username": sample_user["username"],
        "email": sample_user["email"],
        "role": sample_user["role"],
        "hashed_password": security_manager.get_password_hash(sample_user["password"]),
        "created_at": datetime.utcnow().isoformat(),
        "password_changed_at": datetime.utcnow().isoformat(),
        "disabled": False,
        "failed_attempts": 0,
        "locked_until": None
    }
    
    security_manager.save_user(sample_user["username"], user_data)
    
    # Successful authentication
    auth_user = security_manager.authenticate_user(
        sample_user["username"], 
        sample_user["password"]
    )
    assert auth_user is not None
    assert auth_user["username"] == sample_user["username"]
    
    # Failed authentication - wrong password
    auth_user = security_manager.authenticate_user(
        sample_user["username"], 
        "WrongPassword"
    )
    assert auth_user is None
    
    # Check failed attempts increased
    user = security_manager.get_user(sample_user["username"])
    assert user["failed_attempts"] == 1

def test_account_lockout(security_manager, test_config):
    """Test account lockout after failed attempts"""
    username = "locktest"
    password = "TestPassword123!"
    
    # Create user
    user_data = {
        "username": username,
        "email": "lock@test.com",
        "hashed_password": security_manager.get_password_hash(password),
        "created_at": datetime.utcnow().isoformat(),
        "failed_attempts": 0,
        "locked_until": None
    }
    
    security_manager.save_user(username, user_data)
    
    # Make multiple failed attempts
    for _ in range(test_config.max_login_attempts):
        security_manager.authenticate_user(username, "WrongPassword")
    
    # Account should be locked
    user = security_manager.get_user(username)
    assert user["failed_attempts"] >= test_config.max_login_attempts
    assert user["locked_until"] is not None
    
    # Authentication should fail even with correct password
    auth_user = security_manager.authenticate_user(username, password)
    assert auth_user is None

def test_password_age_check(security_manager):
    """Test password age checking"""
    username = "agetest"
    
    # Create user with old password
    old_date = (datetime.utcnow() - timedelta(days=100)).isoformat()
    user_data = {
        "username": username,
        "email": "age@test.com",
        "password_changed_at": old_date,
        "created_at": old_date
    }
    
    security_manager.save_user(username, user_data)
    
    # Check password age
    needs_change = security_manager.check_password_age(username)
    assert needs_change

def test_secure_password_generation(security_manager):
    """Test secure password generation"""
    password = security_manager.generate_secure_password()
    
    assert len(password) == 16
    valid, msg = security_manager.validate_password_strength(password)
    assert valid