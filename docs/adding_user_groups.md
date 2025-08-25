# Adding New User Groups and Folders to RAG System

## Overview
The RAG system is designed with excellent modularity that makes adding new user groups and document categories straightforward. You can easily add new roles with their own document folders and access permissions.

## Step-by-Step Process

### Step 1: Add New Document Folder

First, create the physical directory structure:

```bash
# Navigate to documents directory
cd /nvme0n1p2/documents

# Create new folder (example: 'hr' for Human Resources)
sudo mkdir -p hr
sudo chown raguser:raguser hr
sudo chmod 755 hr

# Or create multiple new folders
sudo mkdir -p hr finance legal marketing
sudo chown raguser:raguser hr finance legal marketing
sudo chmod 755 hr finance legal marketing
```

### Step 2: Update Role Permissions in Enhanced Retriever

Edit `src/enhanced_retriever.py` and update the `role_permissions` dictionary:

```python
# In enhanced_retriever.py, find this section:
self.role_permissions = {
    "admin": ["service", "rnd", "archive"],
    "developer": ["service", "rnd"],
    "service": ["service"]
}

# Add your new roles:
self.role_permissions = {
    "admin": ["service", "rnd", "archive", "hr", "finance", "legal", "marketing"],
    "developer": ["service", "rnd"],
    "service": ["service"],
    "hr_manager": ["service", "hr"],           # HR manager can access service + HR docs
    "finance_user": ["service", "finance"],    # Finance user can access service + finance docs
    "legal_counsel": ["service", "legal"],     # Legal counsel can access service + legal docs
    "marketing_lead": ["service", "marketing", "rnd"]  # Marketing can access service, marketing, and R&D
}
```

### Step 3: Update User Creation Script

Edit `src/create_user.py` to include the new roles in validation:

```python
# Find the role validation section and update:
if role not in ["admin", "developer", "service"]:
    raise ValueError(f"Invalid role: {role}")

# Update to:
if role not in ["admin", "developer", "service", "hr_manager", "finance_user", "legal_counsel", "marketing_lead"]:
    raise ValueError(f"Invalid role: {role}")

# Also update the interactive role selection:
print("\nAvailable roles:")
print("  1. admin - Full system access")
print("  2. developer - Access to service and R&D documents")
print("  3. service - Access to service documents only")
print("  4. hr_manager - Access to service and HR documents")
print("  5. finance_user - Access to service and finance documents")
print("  6. legal_counsel - Access to service and legal documents")  
print("  7. marketing_lead - Access to service, marketing, and R&D documents")

# Update the role_map:
role_map = {
    "1": "admin", 
    "2": "developer", 
    "3": "service",
    "4": "hr_manager",
    "5": "finance_user", 
    "6": "legal_counsel",
    "7": "marketing_lead"
}
```

### Step 4: Update User Management Script

Edit `src/user_management.py` to include new roles:

```python
# Find the role validation in change_role method:
if new_role not in ["admin", "developer", "service"]:

# Update to:
if new_role not in ["admin", "developer", "service", "hr_manager", "finance_user", "legal_counsel", "marketing_lead"]:
```

### Step 5: Update Rate Limiting Configuration (Optional)

If you want different rate limits for new roles, update the configuration in `config.py`:

```python
# Add rate limits for new roles
self.rate_limits = {
    "admin": 50,
    "developer": 15,
    "service": 5,
    "hr_manager": 10,
    "finance_user": 8,
    "legal_counsel": 12,
    "marketing_lead": 15
}
```

### Step 6: Update Document Processor (Optional)

If you want automatic categorization of documents into the new folders, update `src/document_processor.py`:

```python
def process_document(self, file_path: str, category: str = "service") -> Dict[str, Any]:
    # Allow specifying category when processing
    # ...existing code...
    
    # Copy to appropriate directory
    category_dir = self.documents_dir / category  # Use specified category
    category_dir.mkdir(exist_ok=True)
    destination = category_dir / file_path.name
    shutil.copy2(file_path, destination)
```

## Quick Example: Adding HR Department

Let's say you want to add an HR department with `hr_manager` and `hr_staff` roles:

### 1. Create Directory
```bash
cd /nvme0n1p2/documents
sudo mkdir -p hr
sudo chown raguser:raguser hr
sudo chmod 755 hr
```

### 2. Update Role Permissions
```python
self.role_permissions = {
    "admin": ["service", "rnd", "archive", "hr"],
    "developer": ["service", "rnd"],
    "service": ["service"],
    "hr_manager": ["service", "hr"],  # Can access service docs + HR docs
    "hr_staff": ["hr"]                # Only HR documents
}
```

### 3. Create HR Users
```bash
cd /nvme0n1p2
source rag-env/bin/activate

# Create HR manager
python src/create_user.py --batch \
  --username hr_manager \
  --email hr.manager@company.com \
  --role hr_manager \
  --password "SecureHRPass123!" \
  --full-name "HR Manager"

# Create HR staff
python src/create_user.py --batch \
  --username hr_staff1 \
  --email hr.staff@company.com \
  --role hr_staff \
  --password "SecureHRStaff123!" \
  --full-name "HR Staff Member"
```

### 4. Add HR Documents
```bash
# Copy HR documents to the new folder
cp /path/to/hr/documents/* /nvme0n1p2/documents/hr/

# Process HR documents with proper categorization
python src/batch_indexer.py /nvme0n1p2/documents/hr/ --recursive
```

## Advanced Features

### Custom Access Rules
You can create more complex access rules by modifying the `get_user_filters` method:

```python
def get_user_filters(self, user_role: str, user_department: str = None) -> Dict[str, Any]:
    """Get document filters based on user role and department"""
    
    # Base permissions
    allowed_categories = self.role_permissions.get(user_role, ["service"])
    
    # Department-specific rules
    if user_department == "sensitive":
        # Only show documents marked as non-sensitive for regular users
        return {
            "$and": [
                {"$or": [{"category": cat} for cat in allowed_categories]},
                {"$or": [{"sensitive": {"$ne": True}}, {"sensitive": {"$exists": False}}]}
            ]
        }
    
    return {"$or": [{"category": cat} for cat in allowed_categories]}
```

### Hierarchical Permissions
You can implement hierarchical permissions:

```python
# Department hierarchies
DEPARTMENT_HIERARCHY = {
    "ceo": ["service", "rnd", "archive", "hr", "finance", "legal", "marketing"],
    "department_head": ["service", "hr", "finance"],  # Multi-department access
    "team_lead": ["service"],  # Base access for all team leads
}

def get_role_permissions(self, user_role: str, user_level: str = "staff") -> List[str]:
    """Get permissions based on role and hierarchical level"""
    if user_level in DEPARTMENT_HIERARCHY:
        return DEPARTMENT_HIERARCHY[user_level]
    return self.role_permissions.get(user_role, ["service"])
```

## Testing the New Setup

### 1. Test Document Access
```python
# Test script to verify role-based access
import asyncio
from src.enhanced_retriever import EnhancedRetriever
from config.config import RAGConfig

async def test_role_access():
    config = RAGConfig()
    retriever = EnhancedRetriever(config)
    
    # Test different roles
    roles = ["hr_manager", "hr_staff", "service", "admin"]
    
    for role in roles:
        print(f"\nTesting role: {role}")
        results = await retriever.query("employee handbook", user_role=role)
        print(f"Results found: {len(results)}")
        
        # Check document count
        count = await retriever.get_document_count(role)
        print(f"Accessible documents: {count}")

asyncio.run(test_role_access())
```

### 2. Test User Creation
```bash
# Test creating users with new roles
python src/create_user.py

# Test user management
python src/user_management.py list --details
```

### 3. Test API Access
```bash
# Test authentication with new role
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "hr_manager", "password": "SecureHRPass123!"}'

# Test query with new role permissions
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer [TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{"query": "employee policies", "max_results": 5}'
```

## Directory Structure After Adding New Groups

```
/nvme0n1p2/documents/
├── service/          # Original service documents
├── rnd/             # Original R&D documents  
├── archive/         # Original archived documents
├── quarantine/      # Failed processing files
├── hr/              # NEW: HR department documents
├── finance/         # NEW: Finance department documents
├── legal/           # NEW: Legal department documents
└── marketing/       # NEW: Marketing department documents
```

## Benefits of This Modular Design

1. **Easy Scalability**: Add unlimited departments and roles
2. **Fine-Grained Access Control**: Each role sees only relevant documents
3. **Secure by Default**: New roles have minimal access initially
4. **Flexible Permissions**: Can create complex permission hierarchies
5. **Simple Management**: Standard user management tools work with all roles
6. **Audit Trail**: All access is logged per role/department
7. **Performance**: Role-based filtering happens at the database level

## Maintenance Notes

- **Backup Strategy**: New folders are automatically included in backups
- **Monitoring**: Document counts and access patterns are tracked per role
- **Security**: Each folder maintains proper permissions automatically
- **Updates**: System updates preserve custom role configurations

The modular design makes it incredibly easy to expand the system as your organization grows!