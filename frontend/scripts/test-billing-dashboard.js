#!/usr/bin/env node

/**
 * Script to test the billing dashboard API
 * Note: All current orgs are "demo" and should not send actual stripe billing data.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  console.log('🔐 Logging in...');
  
  const response = await makeApiCall('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email: email,
      password: password
    })
  });
  
  return response.access_token;
}

async function testBillingDashboard(accessToken) {
  console.log('📊 Testing billing dashboard...');
  
  return await makeApiCall('/api/billing/dashboard', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
}

async function main() {
  try {
    console.log('=== Testing Billing Dashboard ===\n');
    console.log('ℹ️  Note: All current orgs are "demo" and should not send actual stripe billing data.\n');
    
    // Use provided credentials
    const email = 'super_admin@cyberiad.ai';
    const password = '3559scoot';
    
    // Login
    const accessToken = await login(email, password);
    console.log('✅ Login successful\n');
    
    // Test billing dashboard
    const dashboardData = await testBillingDashboard(accessToken);
    console.log('✅ Billing dashboard loaded successfully!\n');
    
    console.log('📊 Dashboard Data:');
    console.log(JSON.stringify(dashboardData, null, 2));
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

// Check if fetch is available (Node.js 18+)
if (typeof fetch === 'undefined') {
  console.error('This script requires Node.js 18+ with built-in fetch support.');
  process.exit(1);
}

main().catch(console.error);