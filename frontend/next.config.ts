import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Only use standalone output when not building on Vercel to prevent trace rename errors (ENOENT)
  output: process.env.VERCEL ? undefined : "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;


