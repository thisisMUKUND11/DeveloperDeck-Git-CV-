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
  pitch: string;
  top_skills: string[];
  total_stars: number;
  language_count: number;
  cards: Card[];
  public_count: number;
  private_count: number;
  private_access: boolean;
  generated_with: "gemini" | "claude" | "rules";
  shared: boolean;
}

// FastAPI errors are {detail: string}, except request-validation errors (422),
// where detail is a list of field errors — never surface that raw.
async function errorMessage(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => ({}));
  if (typeof body.detail === "string") return body.detail;
  if (res.status === 422) return "That doesn't look like a valid GitHub username.";
  return `${fallback} (${res.status})`;
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
  if (!res.ok) throw new Error(await errorMessage(res, "Generation failed"));
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
  if (!res.ok) throw new Error(await errorMessage(res, "Could not create link"));
  const data = await res.json();
  return data.token as string;
}

export async function getShare(token: string): Promise<Profile | null> {
  const res = await fetch(`${API_BASE}/api/share/${token}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load shared link (${res.status})`);
  return res.json();
}

export async function recordView(token: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/share/${token}/view`, { method: "POST" });
  } catch {
    /* analytics is best-effort — never block the view */
  }
}

export async function getShareStats(token: string): Promise<number> {
  const res = await fetch(`${API_BASE}/api/share/${token}/stats`, {
    cache: "no-store",
  });
  if (!res.ok) return 0;
  const data = await res.json();
  return (data.views as number) ?? 0;
}
