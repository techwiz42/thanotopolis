#!/usr/bin/env node

/**
 * Script to test organization-specific billing API
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

async function getOrganizations(accessToken) {
  console.log('📋 Getting organizations...');
  
  return await makeApiCall('/api/admin/organizations', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
}

async function testOrgBilling(accessToken, orgId) {
  console.log(`💰 Testing billing for organization ${orgId}...`);
  
  return await makeApiCall(`/api/admin/organizations/${orgId}/billing`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
}

async function main() {
  try {
    console.log('=== Testing Organization-Specific Billing ===\n');
    
    // Use provided credentials
    const email = 'super_admin@cyberiad.ai';
    const password = '3559scoot';
    
    // Login
    const accessToken = await login(email, password);
    console.log('✅ Login successful\n');
    
    // Get organizations
    const orgs = await getOrganizations(accessToken);
    console.log(`📊 Found ${orgs.length} organizations:\n`);
    
    orgs.forEach((org, index) => {
      console.log(`${index + 1}. ${org.name} (${org.subdomain}) - ID: ${org.id}`);
    });
    
    console.log('\n🧪 Testing billing for each organization:\n');
    
    // Test billing for each organization
    for (const org of orgs) {
      try {
        console.log(`\n--- ${org.name} (${org.subdomain}) ---`);
        const billing = await testOrgBilling(accessToken, org.id);
        
        console.log(`✅ Billing data retrieved successfully`);
        console.log(`   Organization: ${billing.organization_name}`);
        console.log(`   Is Demo: ${billing.is_demo}`);
        console.log(`   Current Subscription: ${billing.current_subscription ? 'Yes' : 'No'}`);
        console.log(`   Recent Invoices: ${billing.recent_invoices?.length || 0}`);
        
        if (billing.upcoming_charges) {
          console.log(`   Upcoming Charges: $${(billing.upcoming_charges.total_charges_cents / 100).toFixed(2)}`);
        }
        
      } catch (error) {
        console.error(`❌ Failed to get billing for ${org.name}: ${error.message}`);
      }
    }
    
    console.log('\n✅ Organization billing test completed!');
    
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