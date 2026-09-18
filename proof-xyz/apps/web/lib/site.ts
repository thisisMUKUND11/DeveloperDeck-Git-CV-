/** Canonical public origin of this deployment.
 *
 * Used for OG/canonical metadata, robots.txt and the sitemap — get it wrong and
 * every share preview and indexed URL points at the wrong host.
 *
 * Resolution order:
 *  1. NEXT_PUBLIC_PUBLIC_BASE_URL — set this to your real domain in production.
 *  2. VERCEL_PROJECT_PRODUCTION_URL — injected by Vercel, always the project's
 *     production domain (not the per-deploy preview URL), so a forgotten env
 *     var degrades to "correct host" rather than a stale hardcoded one.
 *  3. localhost, for local builds.
 *
 * Server-only: VERCEL_PROJECT_PRODUCTION_URL is not exposed to the browser.
 * Client components should use `publicBaseUrl()` in SharePanel instead, which
 * falls back to window.location.origin.
 */
/** Drop a trailing slash so callers can safely append "/s/<token>". */
export function normalizeOrigin(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

function resolve(): string {
  const explicit = process.env.NEXT_PUBLIC_PUBLIC_BASE_URL;
  if (explicit?.trim()) return normalizeOrigin(explicit);

  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel?.trim()) {
    return `https://${normalizeOrigin(vercel).replace(/^https?:\/\//, "")}`;
  }

  return "http://localhost:3000";
}

export const SITE_URL = resolve();
