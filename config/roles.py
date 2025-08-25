"""
Central role configuration for the RAG system.
This file defines all available roles and their permissions.
"""

from typing import Dict, List

# Define all available roles and their accessible document categories
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    # Core roles
    "admin": ["service", "rnd", "archive", "hr", "finance", "legal", "marketing"],
    "developer": ["service", "rnd"],
    "service": ["service"],
    
    # HR Department
    "hr_manager": ["service", "hr"],
    "hr_staff": ["hr"],
    
    # Finance Department
    "finance_user": ["service", "finance"],
    "finance_manager": ["service", "finance", "legal"],
    
    # Legal Department
    "legal_counsel": ["service", "legal"],
    
    # Marketing Department
    "marketing_lead": ["service", "marketing", "rnd"],
    
    # Executive roles
    "executive": ["service", "finance", "hr", "legal", "marketing"],
    
    # Add more roles as needed...
}

# Rate limits per role (requests per minute)
ROLE_RATE_LIMITS: Dict[str, int] = {
    "admin": 50,
    "developer": 15,
    "service": 5,
    "hr_manager": 10,
    "hr_staff": 8,
    "finance_user": 8,
    "finance_manager": 12,
    "legal_counsel": 12,
    "marketing_lead": 15,
    "executive": 25,
}

# Role descriptions for UI/documentation
ROLE_DESCRIPTIONS: Dict[str, str] = {
    "admin": "Full system access",
    "developer": "Access to service and R&D documents",
    "service": "Access to service documents only",
    "hr_manager": "Access to service and HR documents",
    "hr_staff": "Access to HR documents only",
    "finance_user": "Access to service and finance documents",
    "finance_manager": "Access to service, finance, and legal documents",
    "legal_counsel": "Access to service and legal documents",
    "marketing_lead": "Access to service, marketing, and R&D documents",
    "executive": "Access to service, finance, HR, legal, and marketing",
}

# Document categories (folders)
DOCUMENT_CATEGORIES: List[str] = [
    "service",
    "rnd",
    "archive",
    "hr",
    "finance",
    "legal",
    "marketing",
    # Add more categories as needed...
]

def get_valid_roles() -> List[str]:
    """Get list of all valid roles"""
    return list(ROLE_PERMISSIONS.keys())

def get_role_permissions(role: str) -> List[str]:
    """Get permissions for a specific role"""
    return ROLE_PERMISSIONS.get(role, ["service"])

def get_role_rate_limit(role: str) -> int:
    """Get rate limit for a specific role"""
    return ROLE_RATE_LIMITS.get(role, 5)

def get_role_description(role: str) -> str:
    """Get description for a specific role"""
    return ROLE_DESCRIPTIONS.get(role, "Unknown role")

def validate_role(role: str) -> bool:
    """Check if a role is valid"""
    return role in ROLE_PERMISSIONS

def validate_category(category: str) -> bool:
    """Check if a document category is valid"""
    return category in DOCUMENT_CATEGORIES