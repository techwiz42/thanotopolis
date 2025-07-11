// Simple test to check if our API service adds the Authorization header
console.log('Testing API service authentication...');

// Mock localStorage
const mockTokens = {
  access_token: "test_token_123",
  refresh_token: "refresh_token_123",
  token_type: "Bearer"
};

// Simulate localStorage content
global.localStorage = {
  getItem: (key) => {
    if (key === 'tokens') return JSON.stringify(mockTokens);
    if (key === 'organization') return 'acme';
    return null;
  }
};

// Mock fetch to capture headers
global.fetch = (url, options) => {
  console.log('Fetch called with:', {
    url,
    method: options.method || 'GET',
    headers: options.headers
  });
  
  // Check if Authorization header is present
  const authHeader = options.headers?.Authorization;
  if (authHeader) {
    console.log('✓ Authorization header found:', authHeader);
  } else {
    console.log('✗ Authorization header missing');
  }
  
  // Check if X-Tenant-ID header is present
  const tenantHeader = options.headers?.['X-Tenant-ID'];
  if (tenantHeader) {
    console.log('✓ X-Tenant-ID header found:', tenantHeader);
  } else {
    console.log('✗ X-Tenant-ID header missing');
  }
  
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ test: 'success' }),
    headers: new Headers()
  });
};

// Test our API service
import('./src/services/api.js').then(({ api }) => {
  console.log('Testing API service...');
  
  // Test GET request
  api.get('/calendar/events').then(() => {
    console.log('GET request test completed');
  }).catch(err => {
    console.error('GET request failed:', err);
  });
  
  // Test POST request
  api.post('/calendar/events', { title: 'Test Event' }).then(() => {
    console.log('POST request test completed');
  }).catch(err => {
    console.error('POST request failed:', err);
  });
  
}).catch(err => {
  console.error('Failed to import API service:', err);
});