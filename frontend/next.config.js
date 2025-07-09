/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Optimize output for better chunk loading
  output: 'standalone',
  // Enable static optimization
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  // Configure static file serving
  assetPrefix: process.env.NODE_ENV === 'production' ? '' : undefined,
  // Production-safe webpack configuration
  webpack: (config, { isServer, dev }) => {
    // Fix webpack chunk loading for server-side rendering
    // This prevents the 'self is not defined' error
    if (isServer) {
      config.output.globalObject = '(typeof self !== "undefined" ? self : this)';
    }
    
    // Only apply memory optimizations in development or when explicitly requested
    if (dev || process.env.WEBPACK_DISABLE_CACHE === 'true') {
      // Limit parallelism to reduce memory usage in development
      config.parallelism = 1;
      
      // Disable caching during builds to save memory
      if (process.env.WEBPACK_DISABLE_CACHE === 'true') {
        config.cache = false;
      }
    }
    
    // Ensure proper chunk splitting for production
    if (!dev) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization.splitChunks,
          chunks: 'all',
          cacheGroups: {
            ...config.optimization.splitChunks.cacheGroups,
            default: {
              minChunks: 2,
              priority: -20,
              reuseExistingChunk: true,
            },
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              priority: -10,
              chunks: 'all',
            },
          },
        },
      };
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
