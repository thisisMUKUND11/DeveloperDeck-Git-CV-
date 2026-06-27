/** @type {import('next').NextConfig} */

// The backend is reached server-side by the Next server, so the browser only
// ever talks to this app's own origin. That means one port to expose when
// sharing (LAN IP or a tunnel) — no separate backend URL for visitors.
const backend = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

const nextConfig = {
  images: {
    remotePatterns: [{ protocol: "https", hostname: "avatars.githubusercontent.com" }],
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  // Allow the dev server to be opened from these origins (LAN / tunnels).
  allowedDevOrigins: ["192.168.1.5", "*.trycloudflare.com", "*.ngrok-free.app"],
};

export default nextConfig;
