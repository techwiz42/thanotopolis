#!/usr/bin/env python3
"""
Create a merge migration to resolve multiple heads
"""

import sys
import os
import subprocess

def create_merge_migration():
    """Create a merge migration"""
    
    # Change to backend directory
    original_cwd = os.getcwd()
    os.chdir('/home/peter/thanotopolis/backend')
    
    try:
        # Create merge migration for the two heads
        result = subprocess.run([
            'alembic', 'merge', '5c22a0233ff8', 'f9a8b7c6d5e4', '-m', 'merge_heads_with_unsubscribe_fields'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Merge migration created successfully!")
            print("Output:", result.stdout)
        else:
            print("❌ Error creating merge migration:")
            print("Error:", result.stderr)
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    create_merge_migration()