#!/usr/bin/env node

/**
 * Simple test script to verify telephony integration works end-to-end
 */

const WebSocket = require('ws');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);
const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

async function testTelephonyIntegration() {
  console.log('🧪 Testing Telephony Integration End-to-End...\n');

  try {
    // 1. Check backend health
    console.log('1️⃣ Checking backend health...');
    const { stdout } = await execAsync(`curl -s ${BACKEND_URL}/health`);
    const healthData = JSON.parse(stdout);
    console.log('✅ Backend health:', healthData);
    
    if (!healthData.features.telephony) {
      throw new Error('Telephony not enabled in backend');
    }
    console.log('✅ Telephony enabled in backend\n');

    // 2. Try to connect to WebSocket without authentication (should work for Twilio)
    console.log('2️⃣ Testing WebSocket connection without auth...');
    const testCallId = '550e8400-e29b-41d4-a716-446655440000'; // Random UUID
    const wsUrl = `${WS_URL}/api/ws/telephony/stream/${testCallId}`;
    
    const ws = new WebSocket(wsUrl);
    
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error('WebSocket connection timeout'));
      }, 5000);

      ws.on('open', () => {
        clearTimeout(timeout);
        console.log('✅ WebSocket connected successfully');
        
        // Send a test message
        ws.send(JSON.stringify({
          type: 'test_message',
          message: 'Hello from test script'
        }));
        
        setTimeout(() => {
          ws.close();
          resolve();
        }, 1000);
      });

      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          console.log('📨 Received message:', message);
        } catch (e) {
          console.log('📨 Received non-JSON message:', data.toString());
        }
      });

      ws.on('error', (error) => {
        clearTimeout(timeout);
        reject(error);
      });

      ws.on('close', (code, reason) => {
        console.log(`🔌 WebSocket closed: ${code} ${reason}`);
      });
    });
    
    console.log('✅ WebSocket test completed\n');

    // 3. Check API routes
    console.log('3️⃣ Checking API routes...');
    const { stdout: routesStdout } = await execAsync(`curl -s ${BACKEND_URL}/debug/routes`);
    const routesData = JSON.parse(routesStdout);
    const telephonyRoutes = routesData.routes.filter(route => 
      route.path.includes('telephony') || route.path.includes('ws')
    );
    
    console.log('📋 Available telephony/websocket routes:');
    telephonyRoutes.forEach(route => {
      console.log(`   ${route.methods.join(', ')} ${route.path}`);
    });
    console.log('✅ API routes available\n');

    console.log('🎉 All tests passed! Telephony integration is working.\n');
    
    console.log('📋 Next steps to test with frontend:');
    console.log('1. Start the frontend: npm run dev');
    console.log('2. Navigate to /organizations/telephony/test');
    console.log('3. Click "Simulate Incoming Call"');
    console.log('4. Check browser console and network tab for WebSocket activity');
    console.log('5. Verify that call records are created in the database\n');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    
    if (error.response) {
      console.error('   Response status:', error.response.status);
      console.error('   Response data:', error.response.data);
    }
    
    process.exit(1);
  }
}

// Run the test
testTelephonyIntegration();