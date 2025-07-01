#!/usr/bin/env node

/**
 * Script to run database migrations for Stripe billing tables
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
    console.log('=== Running Database Migrations for Stripe Billing ===\n');
    
    // Check current migration status
    console.log('📋 Checking current migration status...');
    await runCommand('alembic', ['current'], BACKEND_PATH);
    
    console.log('\n📋 Checking migration history...');
    await runCommand('alembic', ['history'], BACKEND_PATH);
    
    console.log('\n🔄 Running pending migrations...');
    await runCommand('alembic', ['upgrade', 'head'], BACKEND_PATH);
    
    console.log('\n✅ Migrations completed successfully!');
    console.log('Stripe billing tables should now be available.');
    
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    process.exit(1);
  }
}

main().catch(console.error);