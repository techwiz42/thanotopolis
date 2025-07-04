/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Optimize memory usage during builds
  experimental: {
    // Reduce memory usage by limiting worker threads
    workerThreads: false,
    // Reduce memory pressure during builds
    cpus: 1,
  },
  // Optimize webpack for memory usage
  webpack: (config, { isServer }) => {
    // Fix webpack chunk loading for server-side rendering
    // This prevents the 'self is not defined' error
    if (isServer) {
      config.output.globalObject = '(typeof self !== "undefined" ? self : this)';
    }
    
    // Simplified optimization to prevent chunk loading issues
    config.optimization = {
      ...config.optimization,
      splitChunks: {
        ...config.optimization.splitChunks,
        cacheGroups: {
          default: false,
          vendors: false,
        },
      },
    };
    
    // Limit parallelism to reduce memory usage
    config.parallelism = 1;
    
    // Disable caching during builds to save memory
    if (process.env.WEBPACK_DISABLE_CACHE === 'true') {
      config.cache = false;
    }
    
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
      }
    ];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,DELETE,PATCH,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization, X-Tenant-ID' },
        ]
      }
    ];
  }
};

module.exports = nextConfig;
