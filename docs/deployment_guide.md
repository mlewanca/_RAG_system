# Quick Deployment Guide

## 📍 File Storage Location

**All Python files must be stored in: `/nvme0n1p2/`**

This is the main installation directory created by the automated setup script.

## 🚀 Three-Step Deployment

### Step 1: Run Automated Setup
```bash
# Download and run the setup script
curl -fsSL https://your-repo/debian_setup.sh | bash
```

This creates the directory structure and installs all dependencies.

### Step 2: Deploy Python Files
Choose one method:

#### Method A: Git Clone (Recommended)
```bash
cd /nvme0n1p2
git clone <your-repository-url> temp
cp temp/*.py .
cp temp/*.md .
rm -rf temp
```

#### Method B: Direct Download
```bash
cd /nvme0n1p2

# Download all Python files
wget https://your-repo/config.py
wget https://your-repo/security.py
wget https://your-repo/production_api.py
wget https://your-repo/create_user.py
wget https://your-repo/user_management.py
wget https://your-repo/reset_password.py
wget https://your-repo/bulk_user_import.py
wget https://your-repo/user_audit.py
wget https://your-repo/debian_service_manager.py
wget https://your-repo/document_processor.py
wget https://your-repo/batch_indexer.py
wget https://your-repo/enhanced_retriever.py
wget https://your-repo/monitor_processes.py
wget https://your-repo/model_health.py
wget https://your-repo/validate_env.py
wget https://your-repo/test_production.py
wget https://your-repo/validate_security.py
wget https://your-repo/test_password_strength.py
wget https://your-repo/setup_security.py

# Set permissions
chmod 755 *.py
```

### Step 3: Initialize and Start
```bash
cd /nvme0n1p2
source rag-env/bin/activate

# Initialize security
python setup_security.py

# Create users
python create_user.py

# Start services
sudo systemctl start rag-api

# Verify deployment
python debian_service_manager.py health
```

## 📁 Final Directory Layout

After successful deployment, your `/nvme0n1p2/` should contain:

```
/nvme0n1p2/
├── rag-env/                    # Virtual environment (auto-created)
├── config/                     # Configuration (auto-created)
│   ├── .env                   # Environment variables (600)
│   └── users.json             # User database (600)
├── logs/                      # Log files (auto-created)
├── documents/                 # Document storage (auto-created)
├── chroma_db/                 # Vector database (auto-created)
├── backups/                   # Backup directory (auto-created)
│
├── config.py                  # ← YOUR PYTHON FILES GO HERE
├── security.py                # ← ALL .PY FILES IN ROOT DIRECTORY
├── production_api.py          # ← /nvme0n1p2/*.py
├── create_user.py             
├── user_management.py         
├── reset_password.py          
├── bulk_user_import.py        
├── user_audit.py              
├── debian_service_manager.py  
├── document_processor.py      
├── batch_indexer.py           
├── enhanced_retriever.py      
├── monitor_processes.py       
├── model_health.py            
├── validate_env.py            
├── test_production.py         
├── validate_security.py       
├── test_password_strength.py  
├── setup_security.py          
└── requirements.txt           
```

## ⚠️ Important Notes

1. **Always work from `/nvme0n1p2/`**: All scripts expect to run from this directory
2. **Activate virtual environment**: Always run `source rag-env/bin/activate` first
3. **File permissions**: Python files need 755 permissions (`chmod 755 *.py`)
4. **No subdirectories**: Keep all Python files in the root `/nvme0n1p2/` directory
5. **Systemd dependency**: The rag-api service expects files in `/nvme0n1p2/`

## 🔧 Quick Commands

```bash
# Navigate to working directory
cd /nvme0n1p2 && source rag-env/bin/activate

# Check system health
python debian_service_manager.py health

# Create users
python create_user.py

# Manage services
python debian_service_manager.py status

# Run tests
python test_production.py
```

## 🆘 Troubleshooting

### File Not Found Errors
```bash
# Ensure you're in the correct directory
pwd  # Should show /nvme0n1p2

# Check if files exist
ls -la *.py

# Verify virtual environment
source rag-env/bin/activate
which python  # Should show /nvme0n1p2/rag-env/bin/python
```

### Permission Errors
```bash
# Fix file permissions
chmod 755 /nvme0n1p2/*.py
chmod 700 /nvme0n1p2/config
chmod 600 /nvme0n1p2/config/.env
```

### Import Errors
```bash
# Check Python path
cd /nvme0n1p2
python -c "import sys; print(sys.path[0])"  # Should show /nvme0n1p2

# Test imports
python -c "import config, security; print('✅ Imports working')"
```