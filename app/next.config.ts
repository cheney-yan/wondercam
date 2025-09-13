import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: '/',
        destination: '/wondercam',
        permanent: true,
      },
    ];
  },
  async rewrites() {
    // Normalize backend host URL (remove trailing slash)
    const backendHost = (process.env.NEXT_PUBLIC_BACKEND_API_HOST || '').replace(/\/$/, '');
    
    return [
      {
        source: '/v1beta/:path*',
        destination: `${backendHost}/v1beta/:path*`,
      },
      {
        source: '/v2/:path*',
        destination: `${backendHost}/v2/:path*`,
      },
    ]
  },
};

export default nextConfig;
