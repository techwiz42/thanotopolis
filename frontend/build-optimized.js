#!/usr/bin/env node

/**
 * Memory-optimized build script for Next.js applications
 * This script implements several strategies to reduce memory usage during builds
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Configuration
const MEMORY_LIMIT = 1400; // MB - conservative limit for 2GB system
const CHUNK_SIZE = 10; // Number of files to process at once

console.log('🚀 Starting memory-optimized build process...');
console.log(`📊 Memory limit: ${MEMORY_LIMIT}MB`);

// Step 1: Clean up previous builds
console.log('🧹 Cleaning up previous build artifacts...');
const buildDir = path.join(process.cwd(), '.next');
if (fs.existsSync(buildDir)) {
  fs.rmSync(buildDir, { recursive: true, force: true });
}

// Step 2: Set Node.js memory and garbage collection options
const nodeOptions = [
  `--max-old-space-size=${MEMORY_LIMIT}`,
  '--optimize-for-size',
  '--gc-interval=100',
  '--max-semi-space-size=64'
];

console.log('⚙️  Node.js options:', nodeOptions.join(' '));

// Step 3: Run the build with optimized settings
const buildProcess = spawn('node', [
  ...nodeOptions.map(opt => opt),
  'node_modules/.bin/next',
  'build'
], {
  stdio: 'inherit',
  env: {
    ...process.env,
    NODE_ENV: 'production',
    // Reduce parallelism to save memory
    UV_THREADPOOL_SIZE: '2',
    // Webpack optimizations
    WEBPACK_DISABLE_CACHE: 'true',
    // Next.js optimizations
    NEXT_TELEMETRY_DISABLED: '1'
  }
});

buildProcess.on('exit', (code) => {
  if (code === 0) {
    console.log('✅ Build completed successfully!');
  } else {
    console.error(`❌ Build failed with exit code ${code}`);
    process.exit(code);
  }
});

buildProcess.on('error', (error) => {
  console.error('❌ Build process error:', error);
  process.exit(1);
});

// Monitor memory usage
const memoryMonitor = setInterval(() => {
  const memUsage = process.memoryUsage();
  const memMB = Math.round(memUsage.heapUsed / 1024 / 1024);
  if (memMB > MEMORY_LIMIT * 0.8) {
    console.warn(`⚠️  Memory usage high: ${memMB}MB`);
  }
}, 10000);

buildProcess.on('exit', () => {
  clearInterval(memoryMonitor);
});