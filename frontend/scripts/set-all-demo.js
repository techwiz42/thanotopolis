#!/usr/bin/env node

/**
 * Script to set all organizations to demo status
 * Usage: node scripts/set-all-demo.js
 * 
 * This script should be run by a super admin user.
 * It will prompt for credentials and then set all organizations to demo status.
 */

const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

async function makeApiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API call failed: ${response.status} ${response.statusText} - ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`Error calling ${endpoint}:`, error.message);
    throw error;
  }
}

async function login(email, password) {
  console.log('Logging in...');
  
  const response = await makeApiCall('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      username: email,
      password: password
    })
  });
  
  return response.access_token;
}

async function getAllOrganizations(accessToken) {
  console.log('Fetching all organizations...');
  
  return await makeApiCall('/api/admin/organizations', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
}

async function setDemoStatus(tenantId, accessToken) {
  console.log(`Setting organization ${tenantId} to demo status...`);
  
  return await makeApiCall(`/api/billing/set-demo-status/${tenantId}?is_demo=true`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
}

async function main() {
  try {
    console.log('=== Set All Organizations to Demo Status ===\n');
    
    // Get credentials
    const email = await question('Enter super admin email: ');
    const password = await question('Enter password: ');
    
    // Login
    const accessToken = await login(email, password);
    console.log('✅ Login successful\n');
    
    // Get all organizations
    const organizations = await getAllOrganizations(accessToken);
    console.log(`Found ${organizations.length} organizations:\n`);
    
    // Display current status
    organizations.forEach((org, index) => {
      console.log(`${index + 1}. ${org.name} (${org.subdomain}) - Demo: ${org.is_demo ? '✅' : '❌'}`);
    });
    
    console.log('');
    const confirm = await question('Set ALL organizations to demo status? (y/N): ');
    
    if (confirm.toLowerCase() !== 'y' && confirm.toLowerCase() !== 'yes') {
      console.log('Operation cancelled.');
      return;
    }
    
    console.log('\nSetting organizations to demo status...\n');
    
    // Set each organization to demo
    let successCount = 0;
    let errorCount = 0;
    
    for (const org of organizations) {
      try {
        if (!org.is_demo) {
          await setDemoStatus(org.id, accessToken);
          console.log(`✅ ${org.name} set to demo`);
          successCount++;
        } else {
          console.log(`⏭️  ${org.name} already demo`);
        }
      } catch (error) {
        console.error(`❌ Failed to set ${org.name} to demo:`, error.message);
        errorCount++;
      }
    }
    
    console.log(`\n=== Summary ===`);
    console.log(`✅ Successfully set to demo: ${successCount}`);
    console.log(`❌ Errors: ${errorCount}`);
    console.log(`📊 Total organizations: ${organizations.length}`);
    
  } catch (error) {
    console.error('Script failed:', error.message);
    process.exit(1);
  } finally {
    rl.close();
  }
}

// Check if fetch is available (Node.js 18+)
if (typeof fetch === 'undefined') {
  console.error('This script requires Node.js 18+ with built-in fetch support.');
  console.error('Please upgrade your Node.js version or install node-fetch.');
  process.exit(1);
}

main().catch(console.error);