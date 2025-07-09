#!/usr/bin/env python3
"""
Check the current migration state
"""

import sys
import os
import subprocess

def check_migration_state():
    """Check the current migration state"""
    
    # Change to backend directory
    original_cwd = os.getcwd()
    os.chdir('/home/peter/thanotopolis/backend')
    
    try:
        # Check current revision
        print("=== Current Database Revision ===")
        result = subprocess.run([
            'alembic', 'current'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Current:", result.stdout)
        else:
            print("Error:", result.stderr)
            
        # Check heads
        print("\\n=== Available Heads ===")
        result = subprocess.run([
            'alembic', 'heads'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Heads:", result.stdout)
        else:
            print("Error:", result.stderr)
            
        # Check history
        print("\\n=== Migration History ===")
        result = subprocess.run([
            'alembic', 'history'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("History:", result.stdout)
        else:
            print("Error:", result.stderr)
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    check_migration_state()