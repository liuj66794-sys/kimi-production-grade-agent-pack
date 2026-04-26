/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Enable CORS for API routes if needed
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/proxy/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
