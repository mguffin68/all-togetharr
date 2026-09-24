/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "api.dicebear.com" },
      { protocol: "https", hostname: "image.tmdb.org" },
      { protocol: "http", hostname: "localhost" },
    ],
  },
};

export default nextConfig;
