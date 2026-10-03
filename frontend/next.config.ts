import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    const target = process.env.INTERNAL_API_URL || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : null);
    return target ? [{ source: "/api/:path*", destination: `${target}/api/:path*` }] : [];
  },
};

export default nextConfig;
