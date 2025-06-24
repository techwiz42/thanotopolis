#!/usr/bin/env python3
"""
Script to run the call messages migration from the frontend directory.
This changes to the backend directory and runs the alembic migration.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_migration():
    """Run the call messages migration."""
    
    # Get the backend directory path
    frontend_dir = Path(__file__).parent
    backend_dir = frontend_dir.parent / "backend"
    
    if not backend_dir.exists():
        print(f"❌ Backend directory not found at: {backend_dir}")
        return False
    
    if not (backend_dir / "alembic.ini").exists():
        print(f"❌ Alembic configuration not found at: {backend_dir / 'alembic.ini'}")
        return False
    
    print(f"🔍 Backend directory: {backend_dir}")
    print(f"📁 Current directory: {os.getcwd()}")
    
    try:
        # Change to backend directory
        os.chdir(backend_dir)
        print(f"📂 Changed to backend directory: {os.getcwd()}")
        
        # Check current revision
        print("\n📋 Checking current Alembic revision...")
        result = subprocess.run(
            ["alembic", "current"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print(f"✅ Current revision: {result.stdout.strip()}")
        else:
            print(f"⚠️  Could not get current revision: {result.stderr}")
        
        # Check if our migration exists
        migration_file = backend_dir / "alembic" / "versions" / "abc123def456_add_call_messages_table.py"
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        print(f"✅ Migration file exists: {migration_file}")
        
        # Show pending migrations
        print("\n📋 Checking for pending migrations...")
        result = subprocess.run(
            ["alembic", "heads"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print(f"📌 Available heads: {result.stdout.strip()}")
        
        # Run the migration
        print("\n🚀 Running migration to add call messages table...")
        result = subprocess.run(
            ["alembic", "upgrade", "abc123def456"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print(result.stdout)
            return True
        else:
            print("❌ Migration failed!")
            print(f"Error: {result.stderr}")
            print(f"Output: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False
    
    finally:
        # Change back to original directory
        os.chdir(frontend_dir)

def check_migration_status():
    """Check the status after migration."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    try:
        os.chdir(backend_dir)
        
        print("\n📊 Migration Status Check:")
        
        # Check current revision
        result = subprocess.run(
            ["alembic", "current"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print(f"✅ Current revision: {result.stdout.strip()}")
        
        # Check history
        result = subprocess.run(
            ["alembic", "history", "--verbose"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print(f"📜 Migration history:")
            print(result.stdout)
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    finally:
        os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    print("🗄️  Call Messages Migration Script")
    print("=" * 50)
    
    # Run the migration
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        check_migration_status()
    else:
        print("\n💥 Migration failed. Please check the error messages above.")
        sys.exit(1)