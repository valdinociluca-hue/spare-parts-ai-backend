/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@partsai/shared', '@partsai/ui'],
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
