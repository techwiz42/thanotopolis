#!/usr/bin/env node

/**
 * Script to check if Stripe database tables exist
 * Note: All current orgs are "demo" and should not send actual stripe billing data.
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
    console.log('=== Checking Stripe Database Tables ===\n');
    console.log('ℹ️  Note: All current orgs are "demo" and should not send actual stripe billing data.\n');
    
    await client.connect();
    
    // Check if stripe_customers table exists
    const tablesQuery = `
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name LIKE 'stripe_%'
      ORDER BY table_name;
    `;
    
    const result = await client.query(tablesQuery);
    
    if (result.rows.length === 0) {
      console.log('❌ No Stripe tables found in database');
    } else {
      console.log('✅ Found Stripe tables:');
      result.rows.forEach(row => {
        console.log(`  - ${row.table_name}`);
      });
    }
    
    // Check all tables to see what's available
    console.log('\n📋 All tables in database:');
    const allTablesQuery = `
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      ORDER BY table_name;
    `;
    
    const allTables = await client.query(allTablesQuery);
    allTables.rows.forEach(row => {
      console.log(`  - ${row.table_name}`);
    });
    
  } catch (error) {
    console.error('❌ Error checking database:', error.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

main().catch(console.error);