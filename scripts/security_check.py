#!/usr/bin/env python3
"""
Security check script for RAG System
Runs various security scans and provides recommendations
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime

def run_command(cmd, capture_output=True):
    """Run a command and return the result"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode, "", ""
    except Exception as e:
        return 1, "", str(e)

def check_dependencies():
    """Check for vulnerable dependencies"""
    print("\n🔍 Checking Dependencies for Vulnerabilities...")
    print("-" * 50)
    
    # Check if pip-audit is installed
    code, _, _ = run_command("pip show pip-audit")
    if code != 0:
        print("Installing pip-audit...")
        run_command("pip install pip-audit")
    
    # Run pip-audit
    print("Running pip-audit...")
    code, stdout, stderr = run_command("pip-audit --desc")
    
    if code == 0 and "No known vulnerabilities" in stdout:
        print("✅ No vulnerabilities found in dependencies")
    else:
        print("⚠️  Vulnerabilities found:")
        print(stdout)
        
        # Try to auto-fix
        response = input("\nAttempt to auto-fix vulnerabilities? (y/n): ")
        if response.lower() == 'y':
            print("Attempting auto-fix...")
            run_command("pip-audit --fix")

def check_code_security():
    """Run Bandit security linter"""
    print("\n🔍 Checking Code Security...")
    print("-" * 50)
    
    # Check if bandit is installed
    code, _, _ = run_command("pip show bandit")
    if code != 0:
        print("Installing bandit...")
        run_command("pip install bandit")
    
    # Run bandit
    print("Running bandit security scan...")
    code, stdout, stderr = run_command("bandit -r src/ -f json")
    
    try:
        results = json.loads(stdout)
        issues = results.get('results', [])
        
        if not issues:
            print("✅ No security issues found in code")
        else:
            print(f"⚠️  Found {len(issues)} security issues:")
            
            # Group by severity
            by_severity = {}
            for issue in issues:
                severity = issue['issue_severity']
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(issue)
            
            for severity in ['HIGH', 'MEDIUM', 'LOW']:
                if severity in by_severity:
                    print(f"\n{severity} Severity ({len(by_severity[severity])} issues):")
                    for issue in by_severity[severity][:5]:  # Show first 5
                        print(f"  - {issue['issue_text']}")
                        print(f"    File: {issue['filename']}:{issue['line_number']}")
    
    except json.JSONDecodeError:
        print("Could not parse bandit results")
        print(stdout)

def check_secrets():
    """Check for hardcoded secrets"""
    print("\n🔍 Checking for Hardcoded Secrets...")
    print("-" * 50)
    
    # Simple patterns to check
    secret_patterns = [
        ('JWT Secret', r'jwt_secret\s*=\s*["\'][^"\']+["\']'),
        ('API Key', r'api_key\s*=\s*["\'][^"\']+["\']'),
        ('Password', r'password\s*=\s*["\'][^"\']+["\']'),
        ('Token', r'token\s*=\s*["\'][^"\']+["\']'),
    ]
    
    found_secrets = False
    
    for root, dirs, files in os.walk('src'):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text()
                    for pattern_name, pattern in secret_patterns:
                        import re
                        if re.search(pattern, content, re.IGNORECASE):
                            print(f"⚠️  Possible {pattern_name} in {filepath}")
                            found_secrets = True
                except Exception:
                    pass
    
    if not found_secrets:
        print("✅ No hardcoded secrets detected")

def check_requirements():
    """Check requirements for security issues"""
    print("\n🔍 Checking Requirements File...")
    print("-" * 50)
    
    req_file = Path("docs/requirements.txt")
    if not req_file.exists():
        print("❌ requirements.txt not found")
        return
    
    # Check for packages without version pinning
    unpinned = []
    with open(req_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '==' not in line and '>=' not in line:
                    unpinned.append(line)
    
    if unpinned:
        print("⚠️  Packages without version pinning:")
        for pkg in unpinned:
            print(f"  - {pkg}")
        print("\nConsider pinning versions for reproducible builds")
    else:
        print("✅ All packages have version constraints")

def generate_security_report():
    """Generate a security report"""
    print("\n📋 Generating Security Report...")
    print("-" * 50)
    
    report = {
        "scan_date": datetime.now().isoformat(),
        "python_version": sys.version,
        "checks_performed": [
            "dependency_vulnerabilities",
            "code_security",
            "secret_scanning",
            "requirements_check"
        ]
    }
    
    report_path = Path("security_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Security report saved to: {report_path}")

def main():
    """Run all security checks"""
    print("🛡️  RAG System Security Check")
    print("=" * 50)
    
    # Run all checks
    check_dependencies()
    check_code_security()
    check_secrets()
    check_requirements()
    generate_security_report()
    
    print("\n✅ Security check complete!")
    print("\nRecommendations:")
    print("1. Keep all dependencies updated")
    print("2. Review and fix any HIGH severity issues")
    print("3. Never commit secrets to the repository")
    print("4. Run this check regularly (weekly recommended)")

if __name__ == "__main__":
    main()