#!/usr/bin/env node

/**
 * Script to create a new Stripe billing migration
 * Note: All current orgs are "demo" and should not send actual stripe billing data.
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
    console.log('=== Creating New Stripe Billing Migration ===\n');
    console.log('ℹ️  Note: All current orgs are "demo" and should not send actual stripe billing data.\n');
    
    // Create a new migration
    console.log('📝 Creating new migration...');
    await runCommand('alembic', ['revision', '--autogenerate', '-m', 'create_stripe_billing_tables'], BACKEND_PATH);
    
    console.log('\n📋 Checking current migration status...');
    await runCommand('alembic', ['current'], BACKEND_PATH);
    
    console.log('\n🔄 Running the new migration...');
    await runCommand('alembic', ['upgrade', 'head'], BACKEND_PATH);
    
    console.log('\n✅ Migration completed successfully!');
    console.log('Stripe billing tables should now be available.');
    
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    process.exit(1);
  }
}

main().catch(console.error);