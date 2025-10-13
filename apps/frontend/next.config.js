/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || 'http://localhost:3000',
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
  images: {
    domains: ['localhost'],
  },
  typescript: {
    // Type checking is handled by the separate type-check script
    ignoreBuildErrors: false,
  },
  eslint: {
    // ESLint is handled by the separate lint script
    ignoreDuringBuilds: false,
  },
};

module.exports = nextConfig;