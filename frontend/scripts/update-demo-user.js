#!/usr/bin/env node

/**
 * Script to update demo@example.com to be a regular user of the demo organization
 */

const { Client } = require('pg');

const client = new Client({
  host: 'localhost',
  port: 5432,
  database: 'thanotopolis',
  user: 'postgres',
  password: 'postgres'
});

async function main() {
  try {
    console.log('=== Updating demo@example.com User ===\n');
    
    await client.connect();
    
    // First, find the demo organization
    console.log('📋 Finding demo organization...');
    const demoOrgQuery = `
      SELECT id, name, subdomain 
      FROM tenants 
      WHERE subdomain = 'demo'
      LIMIT 1;
    `;
    
    const demoOrgResult = await client.query(demoOrgQuery);
    
    if (demoOrgResult.rows.length === 0) {
      throw new Error('Demo organization not found');
    }
    
    const demoOrg = demoOrgResult.rows[0];
    console.log(`✅ Found demo organization: ${demoOrg.name} (${demoOrg.subdomain})`);
    console.log(`   ID: ${demoOrg.id}\n`);
    
    // Check current user status
    console.log('📋 Checking current user status...');
    const userQuery = `
      SELECT u.id, u.email, u.role, u.tenant_id, t.name as organization_name
      FROM users u
      LEFT JOIN tenants t ON u.tenant_id = t.id
      WHERE u.email = 'demo@example.com'
      LIMIT 1;
    `;
    
    const userResult = await client.query(userQuery);
    
    if (userResult.rows.length === 0) {
      throw new Error('User demo@example.com not found');
    }
    
    const user = userResult.rows[0];
    console.log('Current user status:');
    console.log(`  Email: ${user.email}`);
    console.log(`  Role: ${user.role}`);
    console.log(`  Organization: ${user.organization_name || 'None'}`);
    console.log(`  Tenant ID: ${user.tenant_id || 'None'}\n`);
    
    // Update user to be a regular user of demo organization
    console.log('🔄 Updating user...');
    const updateQuery = `
      UPDATE users 
      SET role = 'user', 
          tenant_id = $1,
          updated_at = NOW()
      WHERE email = 'demo@example.com'
      RETURNING id, email, role, tenant_id;
    `;
    
    const updateResult = await client.query(updateQuery, [demoOrg.id]);
    
    if (updateResult.rows.length > 0) {
      const updatedUser = updateResult.rows[0];
      console.log('✅ User updated successfully!');
      console.log('\nNew user status:');
      console.log(`  Email: ${updatedUser.email}`);
      console.log(`  Role: ${updatedUser.role}`);
      console.log(`  Organization: ${demoOrg.name}`);
      console.log(`  Tenant ID: ${updatedUser.tenant_id}`);
    } else {
      throw new Error('Failed to update user');
    }
    
    // Verify the update
    console.log('\n📋 Verifying update...');
    const verifyQuery = `
      SELECT u.email, u.role, t.name as organization_name, t.subdomain
      FROM users u
      JOIN tenants t ON u.tenant_id = t.id
      WHERE u.email = 'demo@example.com';
    `;
    
    const verifyResult = await client.query(verifyQuery);
    
    if (verifyResult.rows.length > 0) {
      const verified = verifyResult.rows[0];
      console.log('✅ Verification successful!');
      console.log(`   ${verified.email} is now a ${verified.role} of ${verified.organization_name} (${verified.subdomain})`);
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

main().catch(console.error);