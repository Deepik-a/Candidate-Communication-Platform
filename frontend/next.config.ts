import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Keep Turbopack rooted in frontend/ so it does not pick up C:\Users\deepz\package-lock.json
  turbopack: {
    root: path.resolve(process.cwd()),
  },
  // Allow HMR when opening the app via the LAN IP shown in `next dev`
  allowedDevOrigins: ["10.57.89.14", "localhost", "127.0.0.1"],
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
