// Empty = same-origin: requests go to "/api/..." on this app and Next proxies
// them to the backend (see next.config.mjs rewrites). This makes the app
// shareable over LAN/tunnel with a single exposed port.
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export interface Card {
  repo: string;
  visibility: "public" | "private";
  locked: boolean;
  languages: string[];
  summary: string;
  why: string[];
  how: string[];
  stat: string;
  skills: string[];
  url: string;
}

export interface Profile {
  username: string;
  name: string | null;
  avatar_url: string | null;
  bio: string | null;
  theme: string;
  headline: string;
  cards: Card[];
  public_count: number;
  private_count: number;
  private_access: boolean;
  generated_with: "gemini" | "claude" | "rules";
  shared: boolean;
}

export async function getProfile(username: string): Promise<Profile | null> {
  const res = await fetch(`${API_BASE}/api/profile/${username}`, {
    // Always fetch fresh — profiles are regenerated on demand.
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load profile (${res.status})`);
  return res.json();
}

export async function generateProfile(
  username: string,
  theme: string,
  token?: string,
): Promise<Profile> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, theme, token: token || null }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Generation failed (${res.status})`);
  }
  return res.json();
}

export async function createShare(
  username: string,
  repos: string[],
  theme: string,
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, repos, theme }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Could not create link (${res.status})`);
  }
  const data = await res.json();
  return data.token as string;
}

export async function getShare(token: string): Promise<Profile | null> {
  const res = await fetch(`${API_BASE}/api/share/${token}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load shared link (${res.status})`);
  return res.json();
}
