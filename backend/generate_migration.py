#!/usr/bin/env python3
"""
Generate Alembic migration for unsubscribe fields
"""

import sys
import os
import subprocess

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

def generate_migration():
    """Generate the Alembic migration"""
    
    # Change to backend directory
    os.chdir('/home/peter/thanotopolis/backend')
    
    try:
        # Run alembic revision command
        result = subprocess.run([
            'alembic', 'revision', '-m', 'Add unsubscribe fields to contacts'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration file created successfully!")
            print("Output:", result.stdout)
            
            # Find the generated migration file
            import glob
            migration_files = glob.glob('alembic/versions/*_add_unsubscribe_fields_to_contacts.py')
            if migration_files:
                latest_migration = max(migration_files, key=os.path.getctime)
                print(f"Migration file: {latest_migration}")
                return latest_migration
            else:
                print("Could not find generated migration file")
                return None
        else:
            print("❌ Error generating migration:")
            print("Error:", result.stderr)
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    generate_migration()