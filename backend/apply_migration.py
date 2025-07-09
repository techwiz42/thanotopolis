#!/usr/bin/env python3
"""
Apply the Alembic migration for unsubscribe fields
"""

import sys
import os
import subprocess

def apply_migration():
    """Apply the Alembic migration"""
    
    # Change to backend directory
    original_cwd = os.getcwd()
    os.chdir('/home/peter/thanotopolis/backend')
    
    try:
        # Run alembic upgrade command
        result = subprocess.run([
            'alembic', 'upgrade', 'head'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration applied successfully!")
            print("Output:", result.stdout)
        else:
            print("❌ Error applying migration:")
            print("Error:", result.stderr)
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    apply_migration()