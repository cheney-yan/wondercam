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
    return [
      {
        source: '/v1beta/:path*',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_API_HOST}/v1beta/:path*`,
      },
    ]
  },
};

export default nextConfig;
