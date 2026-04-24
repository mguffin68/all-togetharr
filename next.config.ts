import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["react"],
  images: {
    domains: ["localhost"],
    remotePatterns: [],
  },
  experimental: {
    serverActions: {},
  },
};

export default nextConfig;
