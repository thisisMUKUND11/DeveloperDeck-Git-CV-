import type { Profile } from "./api";

// Server-only base URL. OG-image routes and server components can't use a
// relative "/api" path (no origin), so they hit the backend directly.
const SERVER_API_BASE = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

// Share snapshots are immutable once created, so cache them in Next's data
// cache: generateMetadata, the page and the OG image all need the same snapshot,
// and repeat opens of a link no longer round-trip to the API at all.
const SHARE_REVALIDATE_SECONDS = 60 * 60 * 24;

export async function getShareServer(token: string): Promise<Profile | null> {
  const res = await fetch(`${SERVER_API_BASE}/api/share/${token}`, {
    next: { revalidate: SHARE_REVALIDATE_SECONDS },
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
interface OgColors {
  bg: string;
  ink: string;
  muted: string;
  accent: string;
}

const OG_DEFAULT: OgColors = { bg: "#0c0e16", ink: "#eef1f8", muted: "#8b92a6", accent: "#7c6cff" };

export const OG_THEME: Record<string, OgColors> = {
  midnight: OG_DEFAULT,
  paper: { bg: "#fafaf8", ink: "#15171d", muted: "#6b7280", accent: "#3b5bff" },
  sunset: { bg: "#fff2ec", ink: "#2a1a16", muted: "#9a7d72", accent: "#fb5d3b" },
  terminal: { bg: "#07100a", ink: "#d6f5df", muted: "#5f8f73", accent: "#28e07a" },
};

export function ogTheme(id: string): OgColors {
  return OG_THEME[id] ?? OG_DEFAULT;
}
