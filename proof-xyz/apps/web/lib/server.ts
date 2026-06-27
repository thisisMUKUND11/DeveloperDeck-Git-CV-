import type { Profile } from "./api";

// Server-only base URL. OG-image routes and server components can't use a
// relative "/api" path (no origin), so they hit the backend directly.
const SERVER_API_BASE =
  process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

export async function getShareServer(token: string): Promise<Profile | null> {
  const res = await fetch(`${SERVER_API_BASE}/api/share/${token}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function getProfileServer(username: string): Promise<Profile | null> {
  const res = await fetch(`${SERVER_API_BASE}/api/profile/${username}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

// Concrete (non-CSS-var) theme colors for OG image rendering, keyed by theme id.
export const OG_THEME: Record<
  string,
  { bg: string; ink: string; muted: string; accent: string }
> = {
  midnight: { bg: "#0c0e16", ink: "#eef1f8", muted: "#8b92a6", accent: "#7c6cff" },
  paper: { bg: "#fafaf8", ink: "#15171d", muted: "#6b7280", accent: "#3b5bff" },
  sunset: { bg: "#fff2ec", ink: "#2a1a16", muted: "#9a7d72", accent: "#fb5d3b" },
};

export function ogTheme(id: string) {
  return OG_THEME[id] ?? OG_THEME.midnight;
}
