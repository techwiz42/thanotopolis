#!/usr/bin/env python3
"""
Backend Setup Script for Multi-Tenant Auth System
Run this from the project root directory.
"""

import os
import sys
from pathlib import Path

def create_directory_structure():
    """Create the backend directory structure."""
    directories = [
        "backend/app/api",
        "backend/app/db", 
        "backend/app/schemas",
        "backend/tests",
        "backend/alembic"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_init_files():
    """Create __init__.py files."""
    init_files = [
        "backend/app/__init__.py",
        "backend/app/api/__init__.py",
        "backend/app/auth/__init__.py",
        "backend/app/core/__init__.py",
        "backend/app/db/__init__.py",
        "backend/app/models/__init__.py",
        "backend/app/schemas/__init__.py",
        "backend/tests/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch(exist_ok=True)
        print(f"✓ Created file: {init_file}")

def create_requirements_txt():
    """Create requirements.txt file."""
    requirements = """fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic[email]==2.5.2
pydantic-settings==2.1.0
alembic==1.12.1
pytest==7.4.3
httpx==0.25.2"""
    
    with open("backend/requirements.txt", "w") as f:
        f.write(requirements)
    print("✓ Created file: backend/requirements.txt")

def create_env_example():
    """Create .env.example file."""
    env_content = """# Database
DATABASE_URL=postgresql://user:password@localhost/multitenantdb

# Security
SECRET_KEY=your-secret-key-here-use-secrets-token-urlsafe-32

# Application
APP_NAME="Multi-Tenant Auth API"
DEBUG=True

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]"""
    
    with open("backend/.env.example", "w") as f:
        f.write(env_content)
    print("✓ Created file: backend/.env.example")

def create_gitignore():
    """Create .gitignore file."""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Database
*.db
*.sqlite3

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Alembic
alembic/versions/*.py"""
    
    with open("backend/.gitignore", "w") as f:
        f.write(gitignore_content)
    print("✓ Created file: backend/.gitignore")

def copy_env_file():
    """Copy .env.example to .env if it doesn't exist."""
    if not os.path.exists("backend/.env"):
        import shutil
        shutil.copy("backend/.env.example", "backend/.env")
        print("✓ Created .env from .env.example")
        print("⚠️  Please update backend/.env with your actual database credentials")

def print_file_contents():
    """Print the Python file contents to copy."""
    print("\n" + "="*60)
    print("IMPORTANT: Copy the provided Python files to these locations:")
    print("="*60)
    print("1. backend/app/api/multi_tenant.py")
    print("2. backend/app/db/database.py")
    print("3. backend/app/schemas/schemas.py")
    print("4. backend/app/main.py")
    print("5. Update backend/app/auth/auth.py with provided code")
    print("6. Update backend/app/core/config.py with provided code")
    print("="*60 + "\n")

def main():
    print("Setting up Multi-Tenant Auth Backend...\n")
    
    # Check if we're in the right directory
    if not os.path.exists("backend"):
        print("Creating backend directory...")
        os.makedirs("backend")
    
    create_directory_structure()
    create_init_files()
    create_requirements_txt()
    create_env_example()
    create_gitignore()
    copy_env_file()
    
    print("\n✅ Backend structure created successfully!")
    
    print_file_contents()
    
    print("Next steps:")
    print("1. cd backend")
    print("2. python -m venv venv")
    print("3. Activate virtual environment:")
    print("   - Linux/Mac: source venv/bin/activate")
    print("   - Windows: venv\\Scripts\\activate")
    print("4. pip install -r requirements.txt")
    print("5. Update .env with your database credentials")
    print("6. Copy all provided Python files to their locations")
    print("7. Run: python -m app.main")
    print("\nAPI documentation will be available at http://localhost:8000/docs")

if __name__ == "__main__":
    main()
