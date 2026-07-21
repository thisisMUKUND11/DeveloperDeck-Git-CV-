import type { MetadataRoute } from "next";

const BASE =
  process.env.NEXT_PUBLIC_PUBLIC_BASE_URL ||
  "https://developer-deck-git-cv.vercel.app";

// Sitemap for search engines. Only the public landing page is listed —
// generated profiles (/<username>) and share links (/s/<token>) are dynamic
// and user-specific, so they're intentionally excluded.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: BASE,
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
