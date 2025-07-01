#!/usr/bin/env node

/**
 * Script to run the migration that removes phone_calls-conversations relationship
 * and adds cascade deletes
 */

const { spawn } = require('child_process');
const path = require('path');

const BACKEND_PATH = path.resolve(__dirname, '../../backend');

async function runCommand(command, args, cwd) {
  return new Promise((resolve, reject) => {
    console.log(`Running: ${command} ${args.join(' ')}`);
    console.log(`Working directory: ${cwd}`);
    
    const proc = spawn(command, args, {
      cwd,
      stdio: 'inherit',
      shell: true
    });
    
    proc.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Command failed with exit code ${code}`));
      }
    });
    
    proc.on('error', (error) => {
      reject(error);
    });
  });
}

async function main() {
  try {
    console.log('=== Running Cascade Delete Migration ===\n');
    console.log('This migration will:');
    console.log('1. Remove the relationship between phone_calls and conversations tables');
    console.log('2. Add CASCADE on delete to all foreign key constraints\n');
    
    // Check current migration status
    console.log('📋 Checking current migration status...');
    await runCommand('alembic', ['current'], BACKEND_PATH);
    
    console.log('\n🔄 Running the migration...');
    await runCommand('alembic', ['upgrade', 'head'], BACKEND_PATH);
    
    console.log('\n✅ Migration completed successfully!');
    console.log('- Phone calls and conversations are now separate entities');
    console.log('- Cascade deletes are configured for all relationships');
    
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    console.error('\nTo rollback, run: alembic downgrade -1');
    process.exit(1);
  }
}

main().catch(console.error);